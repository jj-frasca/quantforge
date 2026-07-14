from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy


class TRIXStrategy(BaseStrategy):
    """TRIX momentum: triple-smoothed EMA rate of change, traded as a trend signal.

    Notes:
        Smooth the close with three chained EMAs of span `window` (each pass strips shorter
        cycles), take the bar-over-bar percent change of the triple EMA (TRIX), then smooth
        TRIX with an EMA of span `signal`. Long when the smoothed TRIX is positive (the
        de-noised trend is rising), short when negative, flat at exactly zero. Every EMA uses
        `adjust=False` (recursive, causal) and pct_change is trailing, so the signal at t uses
        only bars up to and including t — no look-ahead. A constant price gives zero rate of
        change -> flat.
    """

    name: ClassVar[str] = "trix"
    research_citations: ClassVar[list[str]] = [
        "Hutson, Jack K. 'Good TRIX'. Technical Analysis of Stocks & Commodities 1, no. 5 (1983)."
    ]

    def __init__(self, window: int = 15, signal: int = 9) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        if signal < 1:
            raise ValueError("signal must be >= 1")
        self.window = window
        self.signal = signal

    @property
    def parameters(self) -> dict[str, object]:
        return {"window": self.window, "signal": self.signal}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        ema1 = close.ewm(span=self.window, adjust=False).mean()
        ema2 = ema1.ewm(span=self.window, adjust=False).mean()
        ema3 = ema2.ewm(span=self.window, adjust=False).mean()
        trix = ema3.pct_change()
        smoothed = trix.ewm(span=self.signal, adjust=False).mean()

        signals = pd.Series(0.0, index=data.index)
        signals.loc[smoothed > 0] = 1.0
        signals.loc[smoothed < 0] = -1.0
        return signals
