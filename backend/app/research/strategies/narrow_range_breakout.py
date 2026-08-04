from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy


class NarrowRangeBreakoutStrategy(BaseStrategy):
    """Volatility-contraction breakout: after the narrowest-range bar in N, trade the way it breaks.

    Notes:
        The bar range (high - low) contracts before it expands -- a low-range "NR" bar (Toby Crabel;
        Linda Raschke's NR7 is window 7) flags a coiled market. When the PREVIOUS bar was the
        narrowest of the trailing `window`, this arms a breakout: go long if today's close breaks
        ABOVE that narrow bar's high, short if it breaks BELOW its low, flat otherwise. Uses the
        prior bar's range/high/low (`.shift(1)`) and a trailing rolling-min range, so the signal at
        t uses only data <= t -- no look-ahead. The only catalog strategy that trades the low->high
        volatility transition rather than a price level or moving average.
    """

    name: ClassVar[str] = "narrow_range_breakout"
    research_citations: ClassVar[list[str]] = [
        "Crabel, Toby. Day Trading with Short Term Price Patterns and Opening Range Breakout. "
        "Traders Press, 1990 (narrow-range / NR7, popularized by Linda Raschke)."
    ]

    def __init__(self, window: int = 7) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        self.window = window

    @property
    def parameters(self) -> dict[str, object]:
        return {"window": self.window}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        high = data["high"]
        low = data["low"]
        close = data["close"]

        bar_range = high - low
        # The prior bar was the narrowest of the trailing window (its range == the rolling min).
        was_narrow = (bar_range == bar_range.rolling(self.window).min()).shift(1).fillna(False)
        prev_high = high.shift(1)
        prev_low = low.shift(1)

        signals = pd.Series(0.0, index=data.index)
        signals.loc[was_narrow & (close > prev_high)] = 1.0
        signals.loc[was_narrow & (close < prev_low)] = -1.0
        return signals
