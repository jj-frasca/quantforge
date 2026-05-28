from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy


class SMAStrategy(BaseStrategy):
    """Simple moving-average crossover: long when fast SMA > slow SMA, short when below.

    Notes:
        No look-ahead: pandas rolling means are trailing (use data up to t), and the engine
        executes on the next bar. During the warmup (before the slow window fills) the signal
        is flat (0.0). No external citation required (textbook).
    """

    name: ClassVar[str] = "sma_crossover"
    research_citations: ClassVar[list[str]] = [
        "Simple moving-average crossover (textbook); no external citation required."
    ]

    def __init__(self, fast: int = 20, slow: int = 50) -> None:
        if fast < 1:
            raise ValueError("fast window must be >= 1")
        if fast >= slow:
            raise ValueError("fast window must be < slow window")
        self.fast = fast
        self.slow = slow

    @property
    def parameters(self) -> dict[str, object]:
        return {"fast": self.fast, "slow": self.slow}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        fast_ma = close.rolling(self.fast).mean()
        slow_ma = close.rolling(self.slow).mean()

        signals = pd.Series(0.0, index=data.index)
        signals.loc[fast_ma > slow_ma] = 1.0
        signals.loc[fast_ma < slow_ma] = -1.0
        return signals
