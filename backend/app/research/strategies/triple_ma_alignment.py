from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy


class TripleMAAlignmentStrategy(BaseStrategy):
    """Three moving averages must agree on direction. Long when fast > medium > slow;
    short when fast < medium < slow; flat when the three disagree.

    Notes:
        Cousin to the basic SMA crossover, but with a stricter agreement rule. Two MAs
        flip-flop on every minor wobble — three at different windows demand a more
        sustained move before all three line up. The result is fewer trades, longer
        holds, and a flat position whenever the trend is ambiguous (the classic
        "don't fight the chop" rule).

        Implementation choices:

        - Three trailing SMAs: `fast < medium < slow`. Enforced in __init__ so an
          inverted setup degenerates safely.
        - Bullish alignment = `fast > medium > slow` AND `medium > slow` (both
          comparisons must hold simultaneously). pandas does this cleanly via
          chained boolean masks; no look-ahead because all three rolling means are
          trailing.
        - During warmup (before the slow window fills) the rolling means are NaN and
          the comparison is `NaN > NaN` -> False, which lands the strategy in the flat
          state. Explicit fillna(False) for clarity.

        Elder's "Triple Screen" (1993) uses three different *timeframes* of the same
        indicator (weekly trend + daily oscillator + intraday entry). We use three
        *windows* on the same daily timeframe because the engine works on a single
        timeframe — the spirit is the same (agreement before action), the mechanic is
        simpler.
    """

    name: ClassVar[str] = "triple_ma_alignment"
    research_citations: ClassVar[list[str]] = [
        "Elder, Alexander. Trading for a Living. Wiley, 1993."
    ]

    def __init__(self, fast: int = 10, medium: int = 30, slow: int = 100) -> None:
        if fast < 1:
            raise ValueError("fast window must be >= 1")
        if medium <= fast:
            raise ValueError("medium window must be > fast")
        if slow <= medium:
            raise ValueError("slow window must be > medium")
        self.fast = fast
        self.medium = medium
        self.slow = slow

    @property
    def parameters(self) -> dict[str, object]:
        return {"fast": self.fast, "medium": self.medium, "slow": self.slow}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        ma_fast = close.rolling(self.fast).mean()
        ma_medium = close.rolling(self.medium).mean()
        ma_slow = close.rolling(self.slow).mean()

        bullish = ((ma_fast > ma_medium) & (ma_medium > ma_slow)).fillna(False)
        bearish = ((ma_fast < ma_medium) & (ma_medium < ma_slow)).fillna(False)

        signals = pd.Series(0.0, index=data.index)
        signals.loc[bullish] = 1.0
        signals.loc[bearish] = -1.0
        return signals
