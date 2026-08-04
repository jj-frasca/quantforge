from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy


class RegimeFilteredTrendStrategy(BaseStrategy):
    """A 2-signal COMBINATION: an SMA crossover taken only when ADX confirms a strong trend regime.

    Notes:
        The direction is a classic fast/slow SMA crossover (long when fast > slow, short when fast <
        slow). The REGIME FILTER is Wilder's ADX (New Concepts in Technical Trading Systems, 1978),
        which measures trend STRENGTH regardless of direction: the crossover is only taken when ADX
        exceeds `adx_threshold`, else the position is flat. This is the point of the combination --
        a moving-average cross whipsaws in a range-bound (low-ADX) market; gating it on trend
        strength sits those periods out. Both signals are trailing (rolling means; Wilder smoothing
        on shifted directional movement) -- no look-ahead; warmup NaNs leave ADX below any positive
        threshold, so the signal stays flat until both inputs are warm.
    """

    name: ClassVar[str] = "regime_filtered_trend"
    research_citations: ClassVar[list[str]] = [
        "Wilder, J. Welles. New Concepts in Technical Trading Systems. Trend Research, 1978 "
        "(ADX regime filter); SMA crossover is a textbook trend signal."
    ]

    def __init__(
        self, fast: int = 20, slow: int = 50, adx_window: int = 14, adx_threshold: float = 25.0
    ) -> None:
        if fast < 1:
            raise ValueError("fast must be >= 1")
        if slow <= fast:
            raise ValueError("slow must be > fast")
        if adx_window < 2:
            raise ValueError("adx_window must be >= 2")
        if not 0.0 < adx_threshold < 100.0:
            raise ValueError("adx_threshold must be in (0, 100)")
        self.fast = fast
        self.slow = slow
        self.adx_window = adx_window
        self.adx_threshold = adx_threshold

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "fast": self.fast,
            "slow": self.slow,
            "adx_window": self.adx_window,
            "adx_threshold": self.adx_threshold,
        }

    def _adx(self, data: pd.DataFrame) -> pd.Series:
        """Wilder's ADX trend-strength line (mirrors ADXStrategy), used here only as a regime gate."""
        high, low, close = data["high"], data["low"], data["close"]
        prev_close = close.shift(1)

        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0.0), 0.0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0.0), 0.0)
        true_range = pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
        ).max(axis=1)

        alpha = 1.0 / self.adx_window
        atr = true_range.ewm(alpha=alpha, adjust=False).mean()
        plus_di = (100.0 * plus_dm.ewm(alpha=alpha, adjust=False).mean() / atr).where(
            atr > 0.0, 0.0
        )
        minus_di = (100.0 * minus_dm.ewm(alpha=alpha, adjust=False).mean() / atr).where(
            atr > 0.0, 0.0
        )
        di_sum = plus_di + minus_di
        dx = (100.0 * (plus_di - minus_di).abs() / di_sum).where(di_sum > 0.0, 0.0)
        return dx.ewm(alpha=alpha, adjust=False).mean()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        fast_ma = close.rolling(self.fast).mean()
        slow_ma = close.rolling(self.slow).mean()

        direction = pd.Series(0.0, index=data.index)
        direction.loc[fast_ma > slow_ma] = 1.0
        direction.loc[fast_ma < slow_ma] = -1.0

        strong = self._adx(data) > self.adx_threshold
        return direction.where(strong, 0.0)
