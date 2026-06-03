from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy


class DonchianBreakoutStrategy(BaseStrategy):
    """Donchian channel breakout: long on new highs, short on new lows.

    Notes:
        At each bar, the signal becomes +1 when the close exceeds the prior `lookback`
        high (a breakout above the channel), and -1 when it drops below the prior
        `lookback` low. Between breakouts the position carries forward (the "trend
        following turtle" rule). Trailing rolling windows mean no look-ahead.
        Made famous by the Turtle Traders experiment (Dennis & Eckhardt, 1983-1988).
    """

    name: ClassVar[str] = "donchian_breakout"
    research_citations: ClassVar[list[str]] = [
        "Faith, Curtis M. Way of the Turtle. McGraw-Hill, 2007."
    ]

    def __init__(self, lookback: int = 20) -> None:
        if lookback < 2:
            raise ValueError("lookback must be >= 2")
        self.lookback = lookback

    @property
    def parameters(self) -> dict[str, object]:
        return {"lookback": self.lookback}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        # shift(1) so the comparison uses bars STRICTLY prior to t — no look-ahead.
        upper = close.shift(1).rolling(self.lookback).max()
        lower = close.shift(1).rolling(self.lookback).min()

        signals = pd.Series(0.0, index=data.index)
        signals.loc[close > upper] = 1.0
        signals.loc[close < lower] = -1.0
        # Carry forward the last breakout — the Turtle rule. ffill() promotes a stale 0
        # though, so replace 0 with NaN, ffill, then fillna with 0 for the warmup region.
        return signals.replace(0.0, pd.NA).ffill().fillna(0.0).astype(float)
