from typing import ClassVar

import numpy as np
import pandas as pd

from app.research.strategies.base import BaseStrategy


class StochasticOscillatorStrategy(BaseStrategy):
    """Stochastic oscillator, traded as mean reversion: long when oversold, short when overbought.

    Notes:
        Fast %K = 100 * (close - lowest_low) / (highest_high - lowest_low) over `k_window`
        (in [0, 100]); the traded line is %D = SMA(%K, `d_window`), the smoothed variant
        that cuts whipsaws. Near 100 the close sits at the window high (overbought → short);
        near 0 at the low (oversold → long). We trade %D crossing `oversold` (default 20) /
        `overbought` (default 80), flat between. Rolling high/low/mean are trailing and use
        only bars up to and including t — no look-ahead. Degenerate case: a flat window
        (highest_high == lowest_low) makes %K undefined; the NaN never trips a threshold, so
        we stay flat.
    """

    name: ClassVar[str] = "stochastic_oscillator"
    research_citations: ClassVar[list[str]] = [
        "Lane, George C. 'Lane's Stochastics'. Technical Analysis of Stocks & Commodities, 1984."
    ]

    def __init__(
        self,
        k_window: int = 14,
        d_window: int = 3,
        oversold: float = 20.0,
        overbought: float = 80.0,
    ) -> None:
        if k_window < 2:
            raise ValueError("k_window must be >= 2")
        if d_window < 1:
            raise ValueError("d_window must be >= 1")
        if not 0.0 < oversold < overbought < 100.0:
            raise ValueError("require 0 < oversold < overbought < 100")
        self.k_window = k_window
        self.d_window = d_window
        self.oversold = oversold
        self.overbought = overbought

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "k_window": self.k_window,
            "d_window": self.d_window,
            "oversold": self.oversold,
            "overbought": self.overbought,
        }

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        high = data["high"]
        low = data["low"]
        close = data["close"]

        highest_high = high.rolling(self.k_window).max()
        lowest_low = low.rolling(self.k_window).min()
        with np.errstate(divide="ignore", invalid="ignore"):
            percent_k = 100.0 * (close - lowest_low) / (highest_high - lowest_low)
        percent_d = percent_k.rolling(self.d_window).mean()

        signals = pd.Series(0.0, index=data.index)
        signals.loc[percent_d < self.oversold] = 1.0
        signals.loc[percent_d > self.overbought] = -1.0
        return signals
