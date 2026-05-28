from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy


class MomentumStrategy(BaseStrategy):
    """Cross-sectional/time-series momentum: long past winners, short past losers.

    Notes:
        Signal is the sign of the trailing return over ``lookback`` bars, ending ``skip`` bars
        ago (the skip avoids short-term reversal). No look-ahead — all inputs are shifted into
        the past. Jegadeesh & Titman (1993).
    """

    name: ClassVar[str] = "momentum"
    research_citations: ClassVar[list[str]] = [
        "Jegadeesh & Titman (1993), Journal of Finance 48(1), pp. 65-91."
    ]

    def __init__(self, lookback: int = 60, skip: int = 5) -> None:
        if lookback < 1:
            raise ValueError("lookback must be >= 1")
        if skip < 0:
            raise ValueError("skip must be >= 0")
        self.lookback = lookback
        self.skip = skip

    @property
    def parameters(self) -> dict[str, object]:
        return {"lookback": self.lookback, "skip": self.skip}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        recent = close.shift(self.skip)
        reference = close.shift(self.skip + self.lookback)
        momentum = recent / reference - 1.0

        signals = pd.Series(0.0, index=data.index)
        signals.loc[momentum > 0] = 1.0
        signals.loc[momentum < 0] = -1.0
        return signals
