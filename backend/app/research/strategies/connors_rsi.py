from typing import ClassVar

import numpy as np
import pandas as pd

from app.research.strategies.base import BaseStrategy


class ConnorsRSIStrategy(BaseStrategy):
    """Connors' short-period RSI mean reversion: buy deep oversold, sell deep overbought.

    Notes:
        Larry Connors popularized trading a very short (2-period) Wilder RSI at extreme
        thresholds (long below ~10, short above ~90) as a mean-reversion entry. RSI uses
        Wilder's recursive smoothing (EMA, alpha = 1/window) of up/down closes -- causal, so
        the signal at t uses only bars up to and including t (no look-ahead). Long when RSI
        < `oversold`, short when RSI > `overbought`, flat between. A constant price yields no
        up/down moves -> RSI undefined -> treated as neutral 50 -> flat.
    """

    name: ClassVar[str] = "connors_rsi"
    research_citations: ClassVar[list[str]] = [
        "Connors, Larry & Alvarez, Cesar. Short Term Trading Strategies That Work. "
        "TradingMarkets Publishing Group, 2009."
    ]

    def __init__(self, window: int = 2, oversold: float = 10.0, overbought: float = 90.0) -> None:
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

        alpha = 1.0 / self.window
        avg_gain = gains.ewm(alpha=alpha, adjust=False).mean()
        avg_loss = losses.ewm(alpha=alpha, adjust=False).mean()

        # avg_loss == 0 with avg_gain > 0 -> rs = +inf -> RSI = 100 (pure uptrend). Both zero
        # (constant price) -> rs = NaN -> RSI NaN -> neutral 50.
        with np.errstate(divide="ignore", invalid="ignore"):
            rs = avg_gain / avg_loss
        rsi = (100.0 - 100.0 / (1.0 + rs)).fillna(50.0)

        signals = pd.Series(0.0, index=data.index)
        signals.loc[rsi < self.oversold] = 1.0
        signals.loc[rsi > self.overbought] = -1.0
        return signals
