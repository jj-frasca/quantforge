from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy


class FiftyTwoWeekHighStrategy(BaseStrategy):
    """Nearness-to-52-week-high momentum (George & Hwang 2004): buy what is near its high.

    Notes:
        Proximity = close / trailing `window`-bar high, in (0, 1]. George & Hwang found stocks
        near their 52-week high (window ~252 trading days) keep outperforming — anchoring makes
        traders under-react to good news. Long when proximity >= `near_high` (at/near the high),
        short when proximity <= `near_low` (deep below it), flat in the band between. The rolling
        max is trailing (uses only bars up to and including t) — no look-ahead; the first `window`
        bars use the available history via `min_periods=1`.
    """

    name: ClassVar[str] = "fifty_two_week_high"
    research_citations: ClassVar[list[str]] = [
        "George, Thomas J., and Chuan-Yang Hwang. 'The 52-Week High and Momentum Investing'. "
        "Journal of Finance 59, no. 5 (2004), pp. 2145-2176."
    ]

    def __init__(self, window: int = 252, near_high: float = 0.95, near_low: float = 0.70) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        if not 0.0 < near_low < near_high <= 1.0:
            raise ValueError("thresholds must satisfy 0 < near_low < near_high <= 1")
        self.window = window
        self.near_high = near_high
        self.near_low = near_low

    @property
    def parameters(self) -> dict[str, object]:
        return {"window": self.window, "near_high": self.near_high, "near_low": self.near_low}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        trailing_high = close.rolling(self.window, min_periods=1).max()
        proximity = close / trailing_high

        signals = pd.Series(0.0, index=data.index)
        signals.loc[proximity >= self.near_high] = 1.0
        signals.loc[proximity <= self.near_low] = -1.0
        return signals
