from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy


class ADXStrategy(BaseStrategy):
    """Wilder's ADX / DMI: trade with the dominant direction only when the trend is strong.

    Notes:
        Directional movement per bar: +DM = up_move when the up_move (high - prev_high) exceeds
        both the down_move (prev_low - low) and zero, else 0; -DM symmetrically. True range TR =
        max(high-low, |high-prev_close|, |low-prev_close|). Wilder-smooth (EMA, alpha = 1/window)
        TR, +DM, -DM; +DI = 100 * smoothed(+DM)/ATR, -DI likewise; DX = 100 * |+DI - -DI| /
        (+DI + -DI); ADX = Wilder-smoothed DX. Long when +DI > -DI AND ADX > `threshold` (a strong
        up-trend), short when -DI > +DI AND ADX > `threshold`, flat when the trend is weak. All
        inputs use `.shift(1)` / trailing smoothing -- no look-ahead. Degenerate (zero-range) bars
        yield 0 directional index, keeping the signal flat.
    """

    name: ClassVar[str] = "adx"
    research_citations: ClassVar[list[str]] = [
        "Wilder, J. Welles. New Concepts in Technical Trading Systems. Trend Research, 1978."
    ]

    def __init__(self, window: int = 14, threshold: float = 25.0) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        if not 0.0 < threshold < 100.0:
            raise ValueError("threshold must be in (0, 100)")
        self.window = window
        self.threshold = threshold

    @property
    def parameters(self) -> dict[str, object]:
        return {"window": self.window, "threshold": self.threshold}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        high = data["high"]
        low = data["low"]
        close = data["close"]
        prev_close = close.shift(1)

        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0.0), 0.0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0.0), 0.0)

        true_range = pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
        ).max(axis=1)

        alpha = 1.0 / self.window
        atr = true_range.ewm(alpha=alpha, adjust=False).mean()
        plus_di = (100.0 * plus_dm.ewm(alpha=alpha, adjust=False).mean() / atr).where(
            atr > 0.0, 0.0
        )
        minus_di = (100.0 * minus_dm.ewm(alpha=alpha, adjust=False).mean() / atr).where(
            atr > 0.0, 0.0
        )

        di_sum = plus_di + minus_di
        dx = (100.0 * (plus_di - minus_di).abs() / di_sum).where(di_sum > 0.0, 0.0)
        adx = dx.ewm(alpha=alpha, adjust=False).mean()

        strong = adx > self.threshold
        signals = pd.Series(0.0, index=data.index)
        signals.loc[strong & (plus_di > minus_di)] = 1.0
        signals.loc[strong & (minus_di > plus_di)] = -1.0
        return signals
