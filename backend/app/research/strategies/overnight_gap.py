from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy


class OvernightGapStrategy(BaseStrategy):
    """Fade the overnight open gap: short large up-gaps, long large down-gaps.

    Notes:
        The gap = today's open / yesterday's close - 1. Overnight moves tend to partially reverse
        (Lou, Polk & Skouras 2019 document a systematic tug-of-war between overnight and intraday
        returns). Long when the gap is below -`threshold` (gapped down -> expect a bounce), short
        when above +`threshold` (gapped up -> expect a fade), flat for small gaps. The gap at t uses
        open_t and close_{t-1}, both known at t's open -- no look-ahead. In this close-to-close
        engine the position is held to earn the following bar's return (the signal predicts
        next-bar reversion, not a same-day intraday fade).
    """

    name: ClassVar[str] = "overnight_gap"
    research_citations: ClassVar[list[str]] = [
        "Lou, Dong, Christopher Polk, and Spyros Skouras. 'A Tug of War: Overnight Versus "
        "Intraday Expected Returns'. Journal of Financial Economics 134, no. 1 (2019)."
    ]

    def __init__(self, threshold: float = 0.02) -> None:
        if not 0.0 < threshold < 1.0:
            raise ValueError("threshold must be in (0, 1)")
        self.threshold = threshold

    @property
    def parameters(self) -> dict[str, object]:
        return {"threshold": self.threshold}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        gap = data["open"] / data["close"].shift(1) - 1.0

        signals = pd.Series(0.0, index=data.index)
        signals.loc[gap > self.threshold] = -1.0  # gapped up -> fade -> short
        signals.loc[gap < -self.threshold] = 1.0  # gapped down -> fade -> long
        return signals
