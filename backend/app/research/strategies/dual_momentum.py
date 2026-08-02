from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy


class DualMomentumStrategy(BaseStrategy):
    """Antonacci dual momentum, single-name: long only when absolute AND relative momentum agree.

    Notes:
        Gary Antonacci's dual momentum (2014) combines two filters. ABSOLUTE momentum is the
        trailing return over `lookback` bars vs cash (proxied here by 0): only hold when the name
        has actually gone up. RELATIVE momentum, cross-sectional in the original, is proxied for a
        single name by requiring the close to sit ABOVE its own longer-term trend (SMA over
        `trend_window`) -- i.e. the recent regime leads the slower one. The strategy is long/flat
        (never short): signal = 1 when trailing return > 0 AND close > trend SMA, else 0. Antonacci
        shows the absolute-momentum gate is what sidesteps the deep drawdowns of always-invested
        momentum. All inputs are trailing (`.shift`, rolling mean) -- no look-ahead; warmup NaNs
        fail both gates and stay flat.
    """

    name: ClassVar[str] = "dual_momentum"
    research_citations: ClassVar[list[str]] = [
        "Antonacci, Gary. Dual Momentum Investing: An Innovative Strategy for Higher Returns "
        "with Lower Risk. McGraw-Hill, 2014."
    ]

    def __init__(self, lookback: int = 120, trend_window: int = 200) -> None:
        if lookback < 1:
            raise ValueError("lookback must be >= 1")
        if trend_window < 2:
            raise ValueError("trend_window must be >= 2")
        self.lookback = lookback
        self.trend_window = trend_window

    @property
    def parameters(self) -> dict[str, object]:
        return {"lookback": self.lookback, "trend_window": self.trend_window}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        absolute_momentum = close / close.shift(self.lookback) - 1.0
        trend = close.rolling(self.trend_window).mean()

        long = (absolute_momentum > 0.0) & (close > trend)
        return long.astype(float)
