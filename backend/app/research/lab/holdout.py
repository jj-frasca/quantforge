from dataclasses import dataclass

import pandas as pd

from app.research.backtesting.engine import BacktestEngine
from app.research.backtesting.metrics import sharpe_ratio
from app.research.strategies.base import BaseStrategy


@dataclass(frozen=True)
class SearchDataHandle:
    """The ONLY data a search tool may touch (ADR-016). Holds strictly the in-sample head, so
    it structurally cannot reach the sealed holdout — search-side functions are typed to accept
    this, never a SealedHoldout, making a leak a type error rather than a silent methodology bug.
    """

    frame: pd.DataFrame
    symbol: str

    @property
    def n_bars(self) -> int:
        return len(self.frame)

    @property
    def years(self) -> float:
        """Calendar span of the in-sample data — the track-record length for the MinTRL gate."""
        span = self.frame.index.max() - self.frame.index.min()
        return float(span.days) / 365.25


class SealedHoldout:
    """The calendar-latest tail, locked away before search. The frame is private: the only way
    to use it is `score_on_holdout`, read exactly once when a finalist is scored (ADR-014/015).
    Metadata (symbol, size, date bounds) is public; the price rows are not."""

    def __init__(self, frame: pd.DataFrame, symbol: str) -> None:
        self._frame = frame
        self.symbol = symbol

    @property
    def n_bars(self) -> int:
        return len(self._frame)

    @property
    def start(self) -> pd.Timestamp:
        return pd.Timestamp(self._frame.index.min())

    @property
    def end(self) -> pd.Timestamp:
        return pd.Timestamp(self._frame.index.max())


@dataclass(frozen=True)
class HoldoutScore:
    sharpe: float
    total_return: float
    n_bars: int
    # Buy-and-hold of the SAME symbol over the holdout — the "why not just hold it?" benchmark.
    # A strategy that trails this on a risk-adjusted basis added no value (ADR-013 / rule 6).
    buy_and_hold_sharpe: float = 0.0


def split_holdout(
    frame: pd.DataFrame,
    symbol: str,
    holdout_fraction: float = 0.2,
    min_holdout_bars: int = 252,
    min_search_bars: int = 252,
) -> tuple[SearchDataHandle, SealedHoldout]:
    """Split a time-ordered daily frame into an in-sample search head and a sealed holdout tail.

    The holdout is always the calendar-latest `max(holdout_fraction·N, min_holdout_bars)` bars.
    Raises if the remaining search head would be shorter than `min_search_bars`.
    """
    if not 0.0 < holdout_fraction < 1.0:
        raise ValueError("holdout_fraction must be in (0, 1)")
    n = len(frame)
    holdout_n = max(int(holdout_fraction * n), min_holdout_bars)
    search_n = n - holdout_n
    if search_n < min_search_bars:
        raise ValueError(
            f"insufficient data: {search_n} search bars after a {holdout_n}-bar holdout "
            f"(need >= {min_search_bars})"
        )
    search_frame = frame.iloc[:search_n]
    holdout_frame = frame.iloc[search_n:]
    return SearchDataHandle(frame=search_frame, symbol=symbol), SealedHoldout(holdout_frame, symbol)


def score_on_holdout(sealed: SealedHoldout, strategy: BaseStrategy) -> HoldoutScore:
    """Run `strategy` on the sealed holdout only and return its out-of-sample score."""
    result = BacktestEngine().run_strategy(sealed._frame, strategy)
    bh_returns = sealed._frame["close"].pct_change().fillna(0.0)
    return HoldoutScore(
        sharpe=result.metrics.sharpe,
        total_return=result.metrics.total_return,
        n_bars=sealed.n_bars,
        buy_and_hold_sharpe=sharpe_ratio(bh_returns),
    )
