from typing import ClassVar

import numpy as np
import pandas as pd

from app.research.strategies.base import BaseStrategy


class WilliamsRStrategy(BaseStrategy):
    """Williams %R oscillator, traded as mean reversion: long when oversold, short when overbought.

    Notes:
        %R = -100 * (highest_high - close) / (highest_high - lowest_low) over a trailing
        `window`, ranging in [-100, 0]. Near -100 the close sits at the window low
        (oversold); near 0 it sits at the high (overbought). We go long when %R < `oversold`
        (default -80) and short when %R > `overbought` (default -20), flat between. Rolling
        high/low are trailing and use only bars up to and including t (OHLC of bar t is known
        at its close) — no look-ahead. Degenerate case: a flat window (highest_high ==
        lowest_low) makes %R undefined; the NaN never trips a threshold, so we stay flat.
    """

    name: ClassVar[str] = "williams_r"
    research_citations: ClassVar[list[str]] = [
        "Williams, Larry. How I Made One Million Dollars Last Year Trading Commodities. "
        "Windsor Books, 1979."
    ]

    def __init__(
        self, window: int = 14, oversold: float = -80.0, overbought: float = -20.0
    ) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        if not -100.0 <= oversold < overbought <= 0.0:
            raise ValueError("require -100 <= oversold < overbought <= 0")
        self.window = window
        self.oversold = oversold
        self.overbought = overbought

    @property
    def parameters(self) -> dict[str, object]:
        return {"window": self.window, "oversold": self.oversold, "overbought": self.overbought}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        high = data["high"]
        low = data["low"]
        close = data["close"]

        highest_high = high.rolling(self.window).max()
        lowest_low = low.rolling(self.window).min()
        span = highest_high - lowest_low
        with np.errstate(divide="ignore", invalid="ignore"):
            percent_r = -100.0 * (highest_high - close) / span

        signals = pd.Series(0.0, index=data.index)
        signals.loc[percent_r < self.oversold] = 1.0
        signals.loc[percent_r > self.overbought] = -1.0
        return signals
