"""The honest state of the research programme in one object (ADR-033 reporting).

Answers the questions a session actually asks: how much has been searched, how many graduates there
are, how many of them are distinguishable from best-of-N selection luck, which ones came closest to
that bar, and whether the deflation survivors are outperforming the non-survivors in the forward
book. Deriving these by hand from the pool is exactly the work that gets re-done every session and
occasionally gets done wrong.

Pure — the caller supplies the experiments and the book.
"""

from collections import Counter, defaultdict
from collections.abc import Container, Sequence

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict

from app.research.lab.calibration import NullCalibration
from app.research.lab.experiment import Experiment, Trial
from app.research.lab.frontier import (
    DetectionFrontier,
    describe_frontier,
    sharpe_standard_error,
)
from app.research.lab.paper import PaperPosition
from app.research.lab.portfolio_manager import DeflationCohorts, deflation_cohorts
from app.research.lab.sharding import shard_universe
from app.research.lab.universe import expected_max_sharpe_under_null, rank_experiments
from app.research.strategies.catalog import CATEGORY_OF

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


class StatisticAgreement(BaseModel):
    """How often the selection-adjusted Sharpe MARGIN the gate uses and the paper's PROBABILITY
    form reach the same verdict on the same finalist (ADR-054).

    Notes:
        `probability_reference` is a stated reading level, not a threshold anything gates on — the
        gate's verdict is the margin one, and switching it would require a fresh Type-I error and
        power curve for the new statistic. These counts are what makes that case arguable with
        measurements; they do not themselves make it.
        Only finalists that CARRY a probability are counted. Treating an unmeasured row as a
        failing one would manufacture a disagreement rate out of rows written before the field.
    """

    model_config = ConfigDict(frozen=True)

    n: int
    probability_reference: float
    both_pass: int
    both_fail: int
    margin_only: int
    probability_only: int
    median_probability: float


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
    # ADR-054: the margin/probability confusion matrix over the pool's finalists. None when no
    # finalist carries a probability — every row written before ADR-054 is in that state.
    statistic_agreement: StatisticAgreement | None = None
    # ADR-060: how far ahead of the runner-up the selected FAMILY was, against Lo's standard
    # error. None when no experiment carries a trial — there is no selection to describe.
    category_separation: "CategorySeparation | None" = None
    # ADR-043: the TRUE edge this design can detect, beside the bar an observation must clear.
    # None when no graduate exists to take a holdout length from — inventing one would publish a
    # detectable edge for a design that was never run.
    frontier: DetectionFrontier | None = None


class CategorySeparation(BaseModel):
    """How far ahead of the runner-up the family the search selected actually was (ADR-060).

    Notes:
        `separable` compares the median gap to Lo (2002)'s Sharpe standard error at the pool's own
        history — a stated statistical scale, not an invented cutoff. It is None, never False, when
        the pool does not state its history: every row written before ADR-052's amendment is in that
        state, and "not measured" must not render as "not separable".
    """

    model_config = ConfigDict(frozen=True)

    medians: dict[str, float]
    winner_shares: dict[str, float]
    median_gap: float
    standard_error: float | None
    separable: bool | None


class NullComparison(BaseModel):
    """One statistic of the pool read against one null mode — ADR-038/039's revisit trigger, run
    in code so a session does not re-derive it by hand.

    Notes:
        `comparable` is the load-bearing field. A difference between two measurements that resolved
        different search families, or that were judged on different history lengths, is not a
        finding about the universe; both mismatches have actually occurred in this repo.
    """

    model_config = ConfigDict(frozen=True)

    statistic: str
    null_mode: str
    real_n: int
    real_median: float
    null_n: int
    null_median: float
    null_p95: float
    # ADR-072: the lower edge of the same band. Reported on every row so a real median under the
    # null is visible, and read as a verdict only where it means something (below).
    null_p5: float = 0.0
    # Stated criterion, not a threshold anything gates on: ADR-038 reads a pool median below the
    # null's p95 as the search producing what it produces from noise.
    real_exceeds_null_p95: bool
    # ADR-072: the mirror criterion, and FALSE BY CONSTRUCTION on the raw rows. Only the excess
    # statistic is centered the same way on both sides (ADR-068); on a raw row the two sides carry
    # different drifts, so a low real median is a fact about drift, not about the search.
    real_below_null_p5: bool = False
    # ADR-075: a 95% interval for real_median - null_median, resampled with the real side CLUSTERED
    # BY SYMBOL. It sizes a different question from the band above — "are the two central tendencies
    # different", not "could one symbol look like this" — so it is reported BESIDE the verdict and
    # never in place of it. None on the raw rows, where the difference is a drift gap.
    difference_ci_low: float | None = None
    difference_ci_high: float | None = None
    difference_n_clusters: int = 0
    comparable: bool
    mismatch: str = ""
    # ADR-064: how many experiments the real side was actually computed from, and their median
    # history. A comparison whose sample the reader cannot see is not a measurement — and after
    # ADR-063 the pool is bimodal, so a pool-wide median describes neither cohort.
    matched_n: int = 0
    matched_n_bars: int | None = None


def _short(version: str) -> str:
    """Abbreviate a fingerprint but never the `legacy-unspecified` sentinel, which truncates into
    something that reads like a hash prefix."""
    return version if len(version) <= 18 else f"{version[:12]}..."


# ADR-064: history length is a QUANTITY, so it gets a tolerance and a subset; the search family is
# an IDENTITY, so it still gets an equality test. The pool's median history grows by a bar per
# trading day, which no fixed artifact can ever equal.
HISTORY_TOLERANCE = 0.10
MIN_MATCHED = 30


def _finalists(experiments: Sequence[Experiment]) -> list[Trial]:
    """The max-DSR trial of every experiment that has one — the window the null artifacts record."""
    return [max(e.trials, key=lambda t: t.deflated_sharpe) for e in experiments if e.trials]


def _matched(experiments: Sequence[Experiment], null_bars: int | None) -> list[Experiment]:
    """The experiments searched over a history within `HISTORY_TOLERANCE` of the null's (ADR-064).

    Notes:
        An experiment that states no `n_bars` is EXCLUDED rather than assumed to match: a row that
        cannot say what produced it cannot be shown to be comparable to anything.
    """
    if null_bars is None:
        return list(experiments)
    return [
        e
        for e in experiments
        if e.n_bars is not None and abs(e.n_bars - null_bars) <= HISTORY_TOLERANCE * null_bars
    ]


def _mismatch(
    report: "PoolReport",
    calibration: NullCalibration,
    matched: Sequence[Experiment],
    matched_diagnostic_n: int,
) -> str:
    """Why this pair cannot be compared, or '' when it can.

    Notes:
        ADR-064 amendment: the search-family test is applied to the MATCHED subset, not to the whole
        pool. The real median is now taken over that subset, so refusing it because of rows that are
        not in it would describe a comparison nobody made — the same defect on the identity side
        that the tolerance fixed on the quantity side. The test itself is unchanged: a fingerprint
        is an identity, and two of them are still two searches.
    """
    reasons = []
    families = {e.search_config_version for e in matched} or set(report.search_config_versions)
    null_family = calibration.search_config_version
    if families and (len(families) > 1 or null_family not in families):
        pool_side = ", ".join(_short(f) for f in sorted(families))
        reasons.append(f"search family {pool_side} vs {_short(null_family)}")
    null_bars = int(np.median(calibration.n_bars)) if calibration.n_bars else None
    pct = int(HISTORY_TOLERANCE * 100)
    if null_bars is not None and not matched:
        reasons.append(f"no experiment's history is within {pct}% of the null's {null_bars} bars")
    elif null_bars is not None and len(matched) < MIN_MATCHED:
        reasons.append(
            f"only {len(matched)} experiments matched {null_bars} bars +/-{pct}% "
            f"(need {MIN_MATCHED} to measure a median)"
        )
    elif matched_diagnostic_n < MIN_MATCHED:
        reasons.append(
            f"only {matched_diagnostic_n} matched diagnostics measured "
            f"(need {MIN_MATCHED} to measure a median)"
        )
    return "; ".join(reasons)


def compare_with_null(
    report: "PoolReport",
    calibrations: Sequence[NullCalibration],
    experiments: Sequence[Experiment] = (),
) -> list[NullComparison]:
    """Read the pool's finalist OOS diagnostics against each null mode's own (ADR-051/064).

    Notes:
        Uses the FINALIST window on both sides: a null artifact records one finalist per searched
        symbol, so the gate-passer window would compare two different statistics — and under
        ADR-046's denominator it is usually empty besides.

        ADR-064: the real side is summarized over the experiments whose history is within
        `HISTORY_TOLERANCE` of THAT artifact's, so one pool in transition can be read against a
        short null and a long one at the same time. When nothing matches, the row still reports the
        pool-wide numbers and refuses — a refusal that hides what it refused teaches nothing.
    """
    rows: list[NullComparison] = []
    for label, pool_wide, null_field, trial_field in (
        (
            "walk-forward",
            report.walk_forward_finalists,
            "walk_forward_oos_sharpes",
            "walk_forward_oos_sharpe",
        ),
        (
            "purged-CV",
            report.purged_cv_finalists,
            "purged_cv_oos_sharpes",
            "purged_cv_oos_sharpe",
        ),
    ):
        for calibration in calibrations:
            values = getattr(calibration, null_field)
            if not values:
                continue
            null_bars = int(np.median(calibration.n_bars)) if calibration.n_bars else None
            matched = _matched(experiments, null_bars)
            matched_bars = [e.n_bars for e in matched if e.n_bars is not None]
            matched_real = _summarize(_finalists(matched), trial_field)
            real = matched_real or pool_wide
            if real is None:
                continue
            array = np.asarray(values, dtype=float)
            p95 = float(np.percentile(array, 95))
            mismatch = _mismatch(
                report,
                calibration,
                matched,
                matched_real.n if matched_real is not None else 0,
            )
            rows.append(
                NullComparison(
                    statistic=label,
                    null_mode=calibration.null_mode,
                    real_n=real.n,
                    real_median=real.median,
                    null_n=len(values),
                    null_median=float(np.median(array)),
                    null_p95=p95,
                    null_p5=float(np.percentile(array, 5)),
                    real_exceeds_null_p95=real.median > p95,
                    comparable=not mismatch,
                    mismatch=mismatch,
                    matched_n=len(matched),
                    matched_n_bars=int(np.median(matched_bars)) if matched_bars else None,
                )
            )
    rows.extend(_excess_rows(report, calibrations, experiments))
    return rows


EXCESS_STATISTIC = "walk-forward excess"


def _clustered_difference_ci(
    real_by_symbol: dict[str, list[float]], null_excess: npt.NDArray[np.float64]
) -> tuple[float, float]:
    """95% interval for `median(real) - median(null)`, resampling the real side BY SYMBOL (ADR-075).

    Notes:
        All of a resampled symbol's experiments enter together, so a name the discovery happened to
        re-search twice cannot inflate the sample it was drawn from. The null side resamples draws,
        which is its natural unit: each null symbol is an independently generated series.

        It sizes a DIFFERENT question from `null_p5`/`null_p95` — whether the two sides' central
        tendencies differ, rather than whether one symbol could look like this — so it is reported
        beside that verdict, never in place of it.

        It does NOT control for cross-sectional correlation: the real symbols share one calendar
        window, so this interval is a LOWER BOUND on the true width. Removing that needs a null
        generated as a correlated panel, which is a change to what the calibration generates.
    """
    clusters = list(real_by_symbol.values())
    rng = np.random.default_rng(_BOOTSTRAP_SEED)
    real_draws = rng.integers(0, len(clusters), size=(_BOOTSTRAP_DRAWS, len(clusters)))
    null_draws = rng.choice(null_excess, size=(_BOOTSTRAP_DRAWS, len(null_excess)))
    differences = [
        float(np.median([v for i in row for v in clusters[i]]) - median)
        for row, median in zip(real_draws, np.median(null_draws, axis=1), strict=True)
    ]
    low, high = np.percentile(differences, [2.5, 97.5])
    return float(low), float(high)


def _excess_rows(
    report: "PoolReport",
    calibrations: Sequence[NullCalibration],
    experiments: Sequence[Experiment],
) -> list[NullComparison]:
    """The same comparison with each side's own drift taken out (ADR-068).

    Notes:
        The walk-forward OOS Sharpe is denominated in the drift of the series it was computed on:
        on both nulls it lands within 0.02 of that generator's own buy-and-hold Sharpe. Comparing
        two raw medians therefore compares two drifts. This row differences each side against what
        holding ITS OWN series across the SAME test blocks earned, so what is left is what the
        search added. Emitted only where both sides measured it — every artifact written before
        ADR-068 carries neither, and an excess of zero is a measurement nobody made (ADR-067).

        The purged-CV row is deliberately absent: its folds are not a prefix-ordered benchmark
        window, so the same subtraction would not be the same statistic.

        ADR-072: this is the ONLY row read two-sided. Because both sides are differenced against
        holding their own series over the same windows, zero means the same thing on each, so a
        real median under the null band is as interpretable as one over it — and it is what the
        pool measured first.
    """
    rows: list[NullComparison] = []
    for calibration in calibrations:
        oos, hold = calibration.walk_forward_oos_sharpes, calibration.walk_forward_hold_sharpes
        # Paired per searched symbol; unequal lengths mean the pairing is unknown, and
        # differencing them anyway would invent a measurement.
        if not hold or len(hold) != len(oos):
            continue
        null_excess = np.asarray(oos, dtype=float) - np.asarray(hold, dtype=float)
        null_bars = int(np.median(calibration.n_bars)) if calibration.n_bars else None
        matched = _matched(experiments, null_bars)
        matched_bars = [e.n_bars for e in matched if e.n_bars is not None]
        real_by_symbol: dict[str, list[float]] = defaultdict(list)
        for e in matched:
            if e.trials is None or e.walk_forward_hold_sharpe is None:
                continue
            finalist = max(e.trials, key=lambda t: t.deflated_sharpe)
            if finalist.walk_forward_oos_sharpe is None:
                continue
            real_by_symbol[e.symbol].append(
                finalist.walk_forward_oos_sharpe - e.walk_forward_hold_sharpe
            )
        real_values = [v for values in real_by_symbol.values() for v in values]
        if not real_values:
            continue
        real_median = float(np.median(np.asarray(real_values, dtype=float)))
        p95 = float(np.percentile(null_excess, 95))
        p5 = float(np.percentile(null_excess, 5))
        mismatch = _mismatch(report, calibration, matched, len(real_values))
        # FINDING-011: the clustered interval is itself a comparison. ADR-064/067's identity and
        # sample guards therefore apply before it can be exposed as an `EXCLUDES ZERO` result.
        low: float | None = None
        high: float | None = None
        n_clusters = len(real_by_symbol) if not mismatch else 0
        if not mismatch and n_clusters >= MIN_MATCHED:
            low, high = _clustered_difference_ci(real_by_symbol, null_excess)
        rows.append(
            NullComparison(
                statistic=EXCESS_STATISTIC,
                null_mode=calibration.null_mode,
                real_n=len(real_values),
                real_median=real_median,
                null_n=len(null_excess),
                null_median=float(np.median(null_excess)),
                null_p95=p95,
                null_p5=p5,
                real_exceeds_null_p95=real_median > p95,
                real_below_null_p5=real_median < p5,
                difference_ci_low=low,
                difference_ci_high=high,
                difference_n_clusters=n_clusters,
                comparable=not mismatch,
                mismatch=mismatch,
                matched_n=len(matched),
                matched_n_bars=int(np.median(matched_bars)) if matched_bars else None,
            )
        )
    return rows


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


def _lifetime_trial_count(experiments: Sequence[Experiment]) -> int:
    """Sum the cumulative DSR/MinTRL denominator once per symbol (ADR-066).

    Each experiment carries prior + current trials, so summing rows counts the same prior once for
    every retained search. Maximum mirrors the experiment-store contract and survives legacy
    counter resets, clock skew, and pool pruning.
    """
    by_symbol: dict[str, int] = {}
    for experiment in experiments:
        by_symbol[experiment.symbol] = max(
            by_symbol.get(experiment.symbol, 0), experiment.lifetime_trials
        )
    return sum(by_symbol.values())


def _agree(
    judged: list[tuple[Trial, float]], probability_reference: float
) -> StatisticAgreement | None:
    """Cross-tabulate the two statistics' verdicts over (finalist, its own dsr_min) pairs."""
    measured = [(t, bar) for t, bar in judged if t.deflated_sharpe_probability is not None]
    if not measured:
        return None
    cells = Counter(
        (
            trial.deflated_sharpe > bar,
            (trial.deflated_sharpe_probability or 0.0) > probability_reference,
        )
        for trial, bar in measured
    )
    return StatisticAgreement(
        n=len(measured),
        probability_reference=probability_reference,
        both_pass=cells[(True, True)],
        both_fail=cells[(False, False)],
        margin_only=cells[(True, False)],
        probability_only=cells[(False, True)],
        median_probability=float(np.median([t.deflated_sharpe_probability for t, _ in measured])),
    )


def _separation(
    experiments: Sequence[Experiment], median_n_bars: int | None
) -> CategorySeparation | None:
    """Group each experiment's finalists by catalog category and report the winner's lead (ADR-060).

    Notes:
        The gap is taken per experiment and then medianed, not taken between the pooled medians:
        the pooled version would compare two different symbols' best families and describe no
        search that ever ran.
    """
    per_category: dict[str, list[float]] = defaultdict(list)
    gaps: list[float] = []
    winners: Counter[str] = Counter()
    for experiment in experiments:
        if not experiment.trials:
            continue
        best: dict[str, float] = {}
        for trial in experiment.trials:
            category = CATEGORY_OF.get(trial.strategy_name)
            if category is None:
                continue
            if category not in best or trial.observed_sharpe > best[category]:
                best[category] = trial.observed_sharpe
        if not best:
            continue
        for covered, sharpe in best.items():
            per_category[covered].append(sharpe)
        winner = max(experiment.trials, key=lambda t: t.deflated_sharpe)
        winning_category = CATEGORY_OF.get(winner.strategy_name)
        if winning_category is not None:
            winners[winning_category] += 1
        ordered = sorted(best.values(), reverse=True)
        if len(ordered) > 1:
            gaps.append(ordered[0] - ordered[1])
    if not per_category or not gaps:
        return None

    n_judged = sum(winners.values())
    median_gap = float(np.median(gaps))
    standard_error = (
        sharpe_standard_error(median_gap, median_n_bars / _TRADING_DAYS) if median_n_bars else None
    )
    return CategorySeparation(
        medians={c: float(np.median(v)) for c, v in per_category.items()},
        winner_shares={c: n / n_judged for c, n in winners.items()} if n_judged else {},
        median_gap=median_gap,
        standard_error=standard_error,
        separable=median_gap > standard_error if standard_error is not None else None,
    )


def summarize_pool(
    experiments: list[Experiment],
    positions: list[PaperPosition],
    *,
    top_near_misses: int = 10,
    probability_reference: float = 0.95,
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
    # Each finalist is judged against the `dsr_min` ITS OWN experiment recorded: the threshold is
    # versioned per experiment (ADR-015/016), so a single pool-wide bar would misreport any row
    # searched under a different rubric.
    judged = [
        (max(e.trials, key=lambda t: t.deflated_sharpe), e.gate_config.dsr_min)
        for e in experiments
        if e.trials
    ]
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
        n_trials=_lifetime_trial_count(experiments),
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
        statistic_agreement=_agree(judged, probability_reference),
        search_config_versions=dict(families.most_common()),
        median_n_bars=int(np.median(searched_bars)) if searched_bars else None,
        frontier=frontier,
        category_separation=_separation(
            experiments, int(np.median(searched_bars)) if searched_bars else None
        ),
    )


# --- ADR-074: the ADR-063 window change, read paired within symbol ---

# ADR-063 moved `SEARCH_HISTORY_START` from 2005 to 1990, which takes a full-history name from
# ~5,450 bars to ~7,400+. A symbol too young for the change to reach lands all its rows on one side
# and drops out of the pairing, which is the conservative direction.
WINDOW_SPLIT_BARS = 6000
_BOOTSTRAP_DRAWS = 20_000
_BOOTSTRAP_SEED = 7
# ADR-076: the nominal two-sided level of each look in a two-look Pocock design whose family-wise
# Type-I is 0.05. ADR-074's criterion was already read once at 0.05; reading its re-run at 0.05 as
# well would spend closer to 0.08 on the one test that could reverse a published decision.
POCOCK_TWO_LOOK_ALPHA = 0.0294


class WindowComparison(BaseModel):
    """What the longer in-sample window did to the finalist the search picks (ADR-074).

    Notes:
        Paired WITHIN symbol and within search family. The cross-symbol form was measured and
        rejected: under one family `n_bars` varies mostly with a symbol's listing age, so the short
        and long cohorts share no symbols and the comparison is between young companies and old
        ones. Repeat runs at the same window collapse to that symbol's median so a name the
        discovery happened to re-search five times does not outweigh one it searched once.

        `oos_delta_*` is denominated in each window's own drift (ADR-068) — the long side's folds
        reach into the 1990s — so it is a surrogate, not the verdict. `excess_delta_*` is the
        drift-controlled statistic ADR-074 judges on, and it stays None until both windows of the
        same symbol carry ADR-068's benchmark. Absent is not zero (ADR-067).
    """

    model_config = ConfigDict(frozen=True)

    n_symbols: int
    short_n_bars: int
    long_n_bars: int
    oos_delta_median: float
    oos_delta_ci_low: float
    oos_delta_ci_high: float
    in_sample_delta_median: float
    in_sample_delta_ci_low: float
    in_sample_delta_ci_high: float
    n_finalist_changed: int
    excess_n: int = 0
    excess_delta_median: float | None = None
    excess_delta_ci_low: float | None = None
    excess_delta_ci_high: float | None = None


class WindowExperiment(BaseModel):
    """ADR-076's frozen answer to ADR-063's second clause, as written by
    `scripts/window_experiment.py report` (ADR-077).

    Notes:
        This is a FROZEN result, not a live derivation. `sample` is the 200 symbols pre-registered
        and committed before any of them was searched; `criterion` is the reading at
        `criterion_alpha`, the Pocock two-look boundary, and it is look 2 of 2 — the sequence is
        closed. `at_look_one_alpha` is the same estimator at the 0.05 look 1 was read at, carried
        alongside so the two bands are never mistaken for one another. Recomputing any of this as
        the pool grows would be a third look the boundary does not cover, which is why nothing
        here derives: it parses.
    """

    model_config = ConfigDict(frozen=True)

    sample: list[str]
    criterion_alpha: float
    criterion: WindowComparison
    at_look_one_alpha: WindowComparison


def _median_ci(values: Sequence[float], alpha: float = 0.05) -> tuple[float, float, float]:
    """Median with a bootstrap interval at two-sided `alpha`. ADR-070: a point estimate with no
    interval is what made two of this project's pre-stated criteria unreadable after the fact.
    ADR-076 reads the same estimator at a stricter alpha when the reading is a repeat look."""
    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(_BOOTSTRAP_SEED)
    draws = rng.choice(array, size=(_BOOTSTRAP_DRAWS, len(array)))
    medians = np.median(draws, axis=1)
    low, high = np.percentile(medians, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(np.median(array)), float(low), float(high)


def window_experiment_workload(
    frozen: Sequence[str], searched: Container[str], *, n_shards: int, shard_index: int
) -> list[str]:
    """What this shard still has to search, out of ADR-076's frozen sample.

    Sharding is applied to the FROZEN sample and only then filtered by what already exists, so a
    resumed run keeps every symbol on the shard it started on. Filtering first would re-pack the
    shards on each restart and make the split depend on how far the previous attempt got.
    """
    return [s for s in shard_universe(list(frozen), n_shards, shard_index) if s not in searched]


def compare_search_windows(
    experiments: Sequence[Experiment], alpha: float = 0.05
) -> WindowComparison | None:
    """Difference each symbol's finalist across the ADR-063 window change, or None when no symbol
    was searched under one family at both windows.

    `alpha` is the two-sided level of every interval returned. It stays at 0.05 for the pool
    report, which is a single look; ADR-076 passes `POCOCK_TWO_LOOK_ALPHA` for the second look at
    its pre-registered sample, so two looks together still spend 0.05.
    """
    by_key: dict[tuple[str, str], list[Experiment]] = defaultdict(list)
    for experiment in experiments:
        if experiment.trials and experiment.n_bars is not None:
            by_key[(experiment.symbol, experiment.search_config_version)].append(experiment)

    oos: list[float] = []
    in_sample: list[float] = []
    excess: list[float] = []
    short_bars: list[int] = []
    long_bars: list[int] = []
    changed = 0
    for group in by_key.values():
        short = [e for e in group if e.n_bars is not None and e.n_bars < WINDOW_SPLIT_BARS]
        long_ = [e for e in group if e.n_bars is not None and e.n_bars >= WINDOW_SPLIT_BARS]
        if not short or not long_:
            continue
        short_finalists = [max(e.trials, key=lambda t: t.deflated_sharpe) for e in short]
        long_finalists = [max(e.trials, key=lambda t: t.deflated_sharpe) for e in long_]
        short_oos = [
            t.walk_forward_oos_sharpe
            for t in short_finalists
            if t.walk_forward_oos_sharpe is not None
        ]
        long_oos = [
            t.walk_forward_oos_sharpe
            for t in long_finalists
            if t.walk_forward_oos_sharpe is not None
        ]
        if not short_oos or not long_oos:
            continue
        oos.append(float(np.median(long_oos) - np.median(short_oos)))
        in_sample.append(
            float(
                np.median([t.observed_sharpe for t in long_finalists])
                - np.median([t.observed_sharpe for t in short_finalists])
            )
        )
        short_bars.append(int(np.median([e.n_bars for e in short if e.n_bars is not None])))
        long_bars.append(int(np.median([e.n_bars for e in long_ if e.n_bars is not None])))
        changed += (
            Counter(t.strategy_name for t in short_finalists).most_common(1)[0][0]
            != Counter(t.strategy_name for t in long_finalists).most_common(1)[0][0]
        )
        short_hold = [
            e.walk_forward_hold_sharpe for e in short if e.walk_forward_hold_sharpe is not None
        ]
        long_hold = [
            e.walk_forward_hold_sharpe for e in long_ if e.walk_forward_hold_sharpe is not None
        ]
        if short_hold and long_hold:
            excess.append(
                float(
                    (np.median(long_oos) - np.median(long_hold))
                    - (np.median(short_oos) - np.median(short_hold))
                )
            )
    if not oos:
        return None

    oos_median, oos_low, oos_high = _median_ci(oos, alpha)
    in_median, in_low, in_high = _median_ci(in_sample, alpha)
    excess_stats = _median_ci(excess, alpha) if excess else None
    return WindowComparison(
        n_symbols=len(oos),
        short_n_bars=int(np.median(short_bars)),
        long_n_bars=int(np.median(long_bars)),
        oos_delta_median=oos_median,
        oos_delta_ci_low=oos_low,
        oos_delta_ci_high=oos_high,
        in_sample_delta_median=in_median,
        in_sample_delta_ci_low=in_low,
        in_sample_delta_ci_high=in_high,
        n_finalist_changed=changed,
        excess_n=len(excess),
        excess_delta_median=excess_stats[0] if excess_stats else None,
        excess_delta_ci_low=excess_stats[1] if excess_stats else None,
        excess_delta_ci_high=excess_stats[2] if excess_stats else None,
    )


def window_experiment_symbols(experiments: Sequence[Experiment], n: int) -> list[str]:
    """The sample for ADR-074 decision 3's pre-registered re-search.

    A symbol qualifies when its LONG window already carries ADR-068's benchmark and its short one
    does not: the re-search supplies the missing side, and the pairing then reads as a
    drift-controlled excess rather than the confounded surrogate. Deterministic (sorted, then a
    seeded shuffle) so re-running the driver hits the same names — a sample that moves between runs
    would let the criterion be re-rolled, which is the failure ADR-070 recorded.
    """
    has_long: set[str] = set()
    has_short: set[str] = set()
    for experiment in experiments:
        if experiment.n_bars is None or experiment.walk_forward_hold_sharpe is None:
            continue
        target = has_long if experiment.n_bars >= WINDOW_SPLIT_BARS else has_short
        target.add(experiment.symbol)
    candidates = sorted(has_long - has_short)
    rng = np.random.default_rng(_BOOTSTRAP_SEED)
    rng.shuffle(candidates)
    return sorted(candidates[:n])
