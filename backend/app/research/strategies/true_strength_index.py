from typing import ClassVar

import numpy as np
import pandas as pd

from app.research.strategies.base import BaseStrategy


class TrueStrengthIndexStrategy(BaseStrategy):
    """True Strength Index (Blau 1991): a double-smoothed momentum oscillator, traded by its sign.

    Notes:
        TSI double-smooths the bar-over-bar price change with two chained EMAs (spans `long_window`
        then `short_window`) and divides by the same double-smoothing of the ABSOLUTE price change,
        scaled to [-100, 100]: TSI = 100 * EMA(EMA(dP)) / EMA(EMA(|dP|)). The double smoothing strips
        most of the noise a single-pass momentum carries, so the sign is a clean trend read. Long
        when TSI is positive (net smoothed momentum up), short when negative, flat at zero. Every EMA
        uses `adjust=False` (recursive, causal) on a shifted diff -- no look-ahead. A flat window
        (zero absolute momentum) makes TSI undefined (0/0 -> NaN); that never trips a threshold, so
        the signal stays flat.
    """

    name: ClassVar[str] = "true_strength_index"
    research_citations: ClassVar[list[str]] = [
        "Blau, William. 'True Strength Index'. Technical Analysis of Stocks & Commodities (1991); "
        "Momentum, Direction, and Divergence (Wiley, 1995)."
    ]

    def __init__(self, long_window: int = 25, short_window: int = 13) -> None:
        if long_window < 2:
            raise ValueError("long_window must be >= 2")
        if short_window < 1:
            raise ValueError("short_window must be >= 1")
        self.long_window = long_window
        self.short_window = short_window

    @property
    def parameters(self) -> dict[str, object]:
        return {"long_window": self.long_window, "short_window": self.short_window}

    def _double_smoothed(self, series: pd.Series) -> pd.Series:
        first = series.ewm(span=self.long_window, adjust=False).mean()
        return first.ewm(span=self.short_window, adjust=False).mean()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        change = data["close"].diff()
        smoothed = self._double_smoothed(change)
        smoothed_abs = self._double_smoothed(change.abs())
        with np.errstate(divide="ignore", invalid="ignore"):
            tsi = 100.0 * smoothed / smoothed_abs

        signals = pd.Series(0.0, index=data.index)
        signals.loc[tsi > 0.0] = 1.0
        signals.loc[tsi < 0.0] = -1.0
        return signals
