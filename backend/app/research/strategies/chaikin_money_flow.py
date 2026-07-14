from typing import ClassVar

import numpy as np
import pandas as pd

from app.research.strategies.base import BaseStrategy


class ChaikinMoneyFlowStrategy(BaseStrategy):
    """Chaikin Money Flow: volume-weighted buying vs selling pressure, traded as a trend signal.

    Notes:
        Each bar's money-flow multiplier = ((close - low) - (high - close)) / (high - low) sits in
        [-1, 1] — +1 when the close is at the high (accumulation), -1 at the low (distribution).
        CMF = sum(multiplier * volume) / sum(volume) over a trailing `window`. Long when CMF >
        `threshold` (net buying), short when CMF < -`threshold` (net selling), flat between. A
        flat bar (high == low) has an undefined multiplier -> treated as zero (no information).
        All rolling sums are trailing -- no look-ahead.
    """

    name: ClassVar[str] = "chaikin_money_flow"
    research_citations: ClassVar[list[str]] = [
        "Chaikin, Marc. Chaikin Money Flow (1980s); see Achelis, Technical Analysis A to Z (2000)."
    ]

    def __init__(self, window: int = 20, threshold: float = 0.05) -> None:
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
        high = data["high"]
        low = data["low"]
        close = data["close"]
        volume = data["volume"]

        span = high - low
        with np.errstate(divide="ignore", invalid="ignore"):
            multiplier = ((close - low) - (high - close)) / span
        # A flat bar (high == low) has no directional money-flow information.
        multiplier = multiplier.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        money_flow_volume = multiplier * volume
        cmf = money_flow_volume.rolling(self.window).sum() / volume.rolling(self.window).sum()

        signals = pd.Series(0.0, index=data.index)
        signals.loc[cmf > self.threshold] = 1.0
        signals.loc[cmf < -self.threshold] = -1.0
        return signals
