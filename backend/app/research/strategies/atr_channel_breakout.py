from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy


class ATRChannelBreakoutStrategy(BaseStrategy):
    """Breakout of an ATR-width channel around a simple moving average, held as a trend.

    Notes:
        Midline is an SMA of close over `ma_window`; the channel sits at midline +/- multiplier *
        ATR, where ATR is Wilder's average true range (EMA with alpha = 1/atr_window). Long when
        the close breaks above the upper band, short when it breaks below the lower band, and --
        unlike the Keltner strategy, which reverts to flat between the bands -- the position is
        CARRIED forward between breakouts (a trend-following hold, the same rule as the Donchian
        breakout). This makes it an ATR-scaled cousin of Donchian: the channel widens with
        volatility so it whipsaws less in chop. True Range uses the prior close via shift(1);
        the SMA and Wilder ATR are trailing -- no look-ahead. A constant (zero-range) series
        never breaks a band and stays flat.
    """

    name: ClassVar[str] = "atr_channel_breakout"
    research_citations: ClassVar[list[str]] = [
        "Kaufman, Perry J. Trading Systems and Methods. 5th ed. Wiley, 2013.",
        "Wilder, J. Welles. New Concepts in Technical Trading Systems. Trend Research, 1978.",
    ]

    def __init__(self, ma_window: int = 20, atr_window: int = 14, multiplier: float = 2.0) -> None:
        if ma_window < 2:
            raise ValueError("ma_window must be >= 2")
        if atr_window < 2:
            raise ValueError("atr_window must be >= 2")
        if multiplier <= 0.0:
            raise ValueError("multiplier must be > 0")
        self.ma_window = ma_window
        self.atr_window = atr_window
        self.multiplier = multiplier

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "ma_window": self.ma_window,
            "atr_window": self.atr_window,
            "multiplier": self.multiplier,
        }

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        high = data["high"]
        low = data["low"]
        close = data["close"]
        prev_close = close.shift(1)

        true_range = pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
        ).max(axis=1)
        atr = true_range.ewm(alpha=1.0 / self.atr_window, adjust=False).mean()

        midline = close.rolling(self.ma_window).mean()
        upper = midline + self.multiplier * atr
        lower = midline - self.multiplier * atr

        signals = pd.Series(0.0, index=data.index)
        signals.loc[close > upper] = 1.0
        signals.loc[close < lower] = -1.0
        # Carry the last breakout forward (trend-follow); replace flat 0 with NaN so ffill
        # doesn't promote a stale reading, then backfill the warmup region with 0.
        return signals.replace(0.0, pd.NA).ffill().fillna(0.0).astype(float)
