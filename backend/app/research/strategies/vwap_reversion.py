from typing import ClassVar

import numpy as np
import pandas as pd

from app.research.strategies.base import BaseStrategy


class VWAPReversionStrategy(BaseStrategy):
    """Mean reversion to the rolling volume-weighted average price (VWAP).

    Notes:
        VWAP over a trailing `window` = sum(typical_price * volume) / sum(volume), where the
        typical price is (high + low + close) / 3. The deviation (close - VWAP) / VWAP measures
        how stretched the price is from where most volume traded. Long when the deviation <
        -`threshold` (price is cheap versus the volume-weighted average -> expect reversion up),
        short when > `threshold`, flat between. Trailing rolling sums -- no look-ahead.
    """

    name: ClassVar[str] = "vwap_reversion"
    research_citations: ClassVar[list[str]] = [
        "Berkowitz, S.A., Logue, D.E., Noser, E.A. 'The Total Cost of Transactions on the NYSE'. "
        "Journal of Finance 43, no. 1 (1988)."
    ]

    def __init__(self, window: int = 20, threshold: float = 0.02) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        if not 0.0 < threshold < 1.0:
            raise ValueError("threshold must be in (0, 1)")
        self.window = window
        self.threshold = threshold

    @property
    def parameters(self) -> dict[str, object]:
        return {"window": self.window, "threshold": self.threshold}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        typical = (data["high"] + data["low"] + close) / 3.0
        volume = data["volume"]
        vwap = (typical * volume).rolling(self.window).sum() / volume.rolling(self.window).sum()
        with np.errstate(divide="ignore", invalid="ignore"):
            deviation = (close - vwap) / vwap

        signals = pd.Series(0.0, index=data.index)
        signals.loc[deviation < -self.threshold] = 1.0
        signals.loc[deviation > self.threshold] = -1.0
        return signals
