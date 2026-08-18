"""The honest state of the research programme in one object (ADR-033 reporting).

Answers the questions a session actually asks: how much has been searched, how many graduates there
are, how many of them are distinguishable from best-of-N selection luck, which ones came closest to
that bar, and whether the deflation survivors are outperforming the non-survivors in the forward
book. Deriving these by hand from the pool is exactly the work that gets re-done every session and
occasionally gets done wrong.

Pure — the caller supplies the experiments and the book.
"""

from pydantic import BaseModel, ConfigDict

from app.research.lab.experiment import Experiment
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
    )
