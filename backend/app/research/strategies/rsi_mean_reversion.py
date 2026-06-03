from typing import ClassVar

import numpy as np
import pandas as pd

from app.research.strategies.base import BaseStrategy


class RSIMeanReversionStrategy(BaseStrategy):
    """RSI-based mean reversion: long when oversold, short when overbought.

    Notes:
        Classic Wilder RSI (1978). When RSI < oversold the asset is treated as oversold
        (long signal); when RSI > overbought the asset is treated as overbought (short).
        Between thresholds the position is flat. Rolling means use a trailing window so
        there's no look-ahead. Returns the SMA-style RSI (mean of gains / mean of losses);
        for a more aggressive variant, replace with Wilder's exponentially-smoothed RSI.
    """

    name: ClassVar[str] = "rsi_mean_reversion"
    research_citations: ClassVar[list[str]] = [
        "Wilder, J. Welles. New Concepts in Technical Trading Systems. Trend Research, 1978."
    ]

    def __init__(self, window: int = 14, oversold: float = 30.0, overbought: float = 70.0) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        if not 0.0 < oversold < overbought < 100.0:
            raise ValueError("require 0 < oversold < overbought < 100")
        self.window = window
        self.oversold = oversold
        self.overbought = overbought

    @property
    def parameters(self) -> dict[str, object]:
        return {"window": self.window, "oversold": self.oversold, "overbought": self.overbought}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        delta = close.diff()
        gains = delta.where(delta > 0, 0.0)
        losses = -delta.where(delta < 0, 0.0)

        avg_gain = gains.rolling(self.window).mean()
        avg_loss = losses.rolling(self.window).mean()

        # Standard RSI edge cases: avg_loss == 0 with avg_gain > 0 → rs = +inf → RSI = 100
        # (pure uptrend in the window). avg_gain == avg_loss == 0 → rs = NaN → neutral 50.
        with np.errstate(divide="ignore", invalid="ignore"):
            rs = avg_gain / avg_loss
        rsi = (100.0 - 100.0 / (1.0 + rs)).fillna(50.0)

        signals = pd.Series(0.0, index=data.index)
        signals.loc[rsi < self.oversold] = 1.0
        signals.loc[rsi > self.overbought] = -1.0
        return signals
