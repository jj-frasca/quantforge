"""The honest state of the research programme in one object (ADR-033 reporting).

Answers the questions a session actually asks: how much has been searched, how many graduates there
are, how many of them are distinguishable from best-of-N selection luck, which ones came closest to
that bar, and whether the deflation survivors are outperforming the non-survivors in the forward
book. Deriving these by hand from the pool is exactly the work that gets re-done every session and
occasionally gets done wrong.

Pure — the caller supplies the experiments and the book.
"""

from collections import Counter

import numpy as np
from pydantic import BaseModel, ConfigDict

from app.research.lab.experiment import Experiment, Trial
from app.research.lab.frontier import DetectionFrontier, describe_frontier
from app.research.lab.paper import PaperPosition
from app.research.lab.portfolio_manager import DeflationCohorts, deflation_cohorts
from app.research.lab.universe import expected_max_sharpe_under_null, rank_experiments

_TRADING_DAYS = 252


class NearMiss(BaseModel):
    """A graduate that failed universe deflation, with how close it came. `ratio_to_bar` is the
    ranking key rather than the raw Sharpe: the bar depends on the holdout length, so a 1.4 Sharpe
    on a 1.6-year holdout is much further away than a 1.2 on a 16-year one."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    strategy_name: str
    holdout_sharpe: float
    bar: float
    ratio_to_bar: float
    holdout_years: float


class DiagnosticSummary(BaseModel):
    """Distribution of one out-of-sample diagnostic across a set of the pool's experiments.

    Notes:
        Exists to be read against the null-calibration percentiles for the SAME statistic
        (ADR-038/039). A median below the null's p95 means the search is producing results
        indistinguishable from what it produces on data with no edge by construction.

        Which set it covers is the caller's choice and it matters (ADR-051): the null artifacts
        record one finalist per SEARCHED symbol, so the finalist window is the comparable one,
        while the gate-passer window answers the narrower question about what was promoted.
    """

    model_config = ConfigDict(frozen=True)

    n: int
    median: float
    p95: float
    maximum: float


class PoolReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    n_experiments: int
    n_symbols: int
    n_trials: int
    n_graduate_experiments: int
    n_leaderboard_graduates: int
    n_surviving_deflation: int
    near_misses: list[NearMiss]
    n_open_positions: int
    book: DeflationCohorts
    # None when no gate passer carries the statistic — every experiment predating ADR-038/039
    # is in that state, and "not measured" must never be read as a measured zero.
    walk_forward_graduates: DiagnosticSummary | None = None
    purged_cv_graduates: DiagnosticSummary | None = None
    # ADR-051: the same statistic over the finalist of EVERY experiment, which is what the null
    # artifacts record. Independent of graduation, so it survives a pool that graduates nothing.
    walk_forward_finalists: DiagnosticSummary | None = None
    purged_cv_finalists: DiagnosticSummary | None = None
    # ADR-052: which resolved hypothesis families produced these rows, with their counts. A pool
    # spanning two families has no single median — it has a blend of two procedures — and this is
    # what lets a reader match the pool against a calibration artifact instead of against git log.
    search_config_versions: dict[str, int] = {}
    # ADR-052: the median history the pool was searched over, to be checked against the null
    # artifact's own n_bars. None when no experiment states one — a median over an empty set would
    # be a fabricated match.
    median_n_bars: int | None = None
    # ADR-043: the TRUE edge this design can detect, beside the bar an observation must clear.
    # None when no graduate exists to take a holdout length from — inventing one would publish a
    # detectable edge for a design that was never run.
    frontier: DetectionFrontier | None = None


def _summarize(trials: list[Trial], field: str) -> DiagnosticSummary | None:
    """Distribution of one nullable Trial diagnostic, or None when none of them carry it."""
    values = [v for t in trials if (v := getattr(t, field)) is not None]
    if not values:
        return None
    array = np.asarray(values, dtype=float)
    return DiagnosticSummary(
        n=len(values),
        median=float(np.median(array)),
        p95=float(np.percentile(array, 95)),
        maximum=float(array.max()),
    )


def summarize_pool(
    experiments: list[Experiment], positions: list[PaperPosition], *, top_near_misses: int = 10
) -> PoolReport:
    """Summarize the research pool and the forward book together.

    `n_graduate_experiments` counts raw graduate rows; `n_leaderboard_graduates` counts distinct
    SYMBOLS that graduated (a name hunted repeatedly collapses to one row), which is the number the
    deflation bar is actually about. Reporting only the former overstates the funnel.
    """
    rows = rank_experiments(experiments)
    n_symbols = len({e.symbol for e in experiments})
    graduates = [r for r in rows if r.graduated]

    # One row per (symbol, strategy): a name re-hunted daily produces near-identical rows, and
    # seven of them would crowd six other names out of the list. Keep each pair's best attempt.
    best_miss: dict[tuple[str, str], NearMiss] = {}
    for experiment in experiments:
        if experiment.graduate is None:
            continue
        g = experiment.graduate
        holdout_years = g.holdout_n_bars / _TRADING_DAYS
        bar = expected_max_sharpe_under_null(n_symbols, holdout_years)
        if bar <= 0 or g.holdout_sharpe > bar:
            continue  # a survivor, or no cross-symbol selection to deflate
        miss = NearMiss(
            symbol=experiment.symbol,
            strategy_name=g.strategy_name,
            holdout_sharpe=g.holdout_sharpe,
            bar=bar,
            ratio_to_bar=g.holdout_sharpe / bar,
            holdout_years=holdout_years,
        )
        key = (miss.symbol, miss.strategy_name)
        current = best_miss.get(key)
        if current is None or miss.ratio_to_bar > current.ratio_to_bar:
            best_miss[key] = miss
    near_misses = sorted(best_miss.values(), key=lambda m: m.ratio_to_bar, reverse=True)

    finalists = [max(e.trials, key=lambda t: t.deflated_sharpe) for e in experiments if e.trials]
    passing_finalists = [
        max(e.trials, key=lambda t: t.deflated_sharpe)
        for e in experiments
        if e.graduate is not None and e.trials
    ]

    # Quoted at the MEDIAN graduate holdout length: a pool mixing 1-year and 10-year holdouts has
    # no single bar, and taking the longest or the shortest would flatter or damn the design by
    # selection (ADR-043).
    holdout_lengths = [e.graduate.holdout_n_bars for e in experiments if e.graduate is not None]
    frontier = (
        describe_frontier(n_symbols, float(np.median(holdout_lengths)) / _TRADING_DAYS)
        if holdout_lengths
        else None
    )

    families = Counter(e.search_config_version for e in experiments)
    searched_bars = [e.n_bars for e in experiments if e.n_bars is not None]

    open_positions = [p for p in positions if p.status == "open"]
    return PoolReport(
        n_experiments=len(experiments),
        n_symbols=n_symbols,
        n_trials=sum(e.lifetime_trials for e in experiments),
        n_graduate_experiments=sum(1 for e in experiments if e.graduate is not None),
        n_leaderboard_graduates=len(graduates),
        n_surviving_deflation=sum(1 for r in graduates if r.survives_universe_deflation),
        near_misses=near_misses[:top_near_misses],
        n_open_positions=len(open_positions),
        book=deflation_cohorts(open_positions),
        walk_forward_graduates=_summarize(passing_finalists, "walk_forward_oos_sharpe"),
        purged_cv_graduates=_summarize(passing_finalists, "purged_cv_oos_sharpe"),
        walk_forward_finalists=_summarize(finalists, "walk_forward_oos_sharpe"),
        purged_cv_finalists=_summarize(finalists, "purged_cv_oos_sharpe"),
        search_config_versions=dict(families.most_common()),
        median_n_bars=int(np.median(searched_bars)) if searched_bars else None,
        frontier=frontier,
    )
