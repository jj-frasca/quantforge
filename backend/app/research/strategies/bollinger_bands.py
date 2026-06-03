from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy


class BollingerBandsStrategy(BaseStrategy):
    """Bollinger Bands mean reversion: long below the lower band, short above the upper.

    Notes:
        Unlike the z-score `mean_reversion` strategy, this one gives a discrete signal
        when the close crosses a fixed-width band (mean +/- num_std * sigma). Position holds
        flat between bands. Bollinger Bands were introduced by John Bollinger in the
        1980s; this implementation uses a Simple Moving Average mean and a sample std
        on a rolling window. No look-ahead.
    """

    name: ClassVar[str] = "bollinger_bands"
    research_citations: ClassVar[list[str]] = [
        "Bollinger, John. Bollinger on Bollinger Bands. McGraw-Hill, 2001."
    ]

    def __init__(self, window: int = 20, num_std: float = 2.0) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        if num_std <= 0:
            raise ValueError("num_std must be > 0")
        self.window = window
        self.num_std = num_std

    @property
    def parameters(self) -> dict[str, object]:
        return {"window": self.window, "num_std": self.num_std}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        mean = close.rolling(self.window).mean()
        std = close.rolling(self.window).std()
        upper = mean + self.num_std * std
        lower = mean - self.num_std * std

        signals = pd.Series(0.0, index=data.index)
        signals.loc[close < lower] = 1.0
        signals.loc[close > upper] = -1.0
        return signals
