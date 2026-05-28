from typing import ClassVar

import pandas as pd

from app.research.strategies.base import BaseStrategy


class MeanReversionStrategy(BaseStrategy):
    """Trade deviations from a rolling mean: short when rich, long when cheap.

    Notes:
        Signal = -clip(z / k, -1, 1) where z is the rolling z-score of price. A price well
        above its mean (z > 0) yields a short. Rolling stats are trailing (no look-ahead).
        Avellaneda & Lee (2010).
    """

    name: ClassVar[str] = "mean_reversion"
    research_citations: ClassVar[list[str]] = [
        "Avellaneda & Lee (2010), Quantitative Finance 10(7), pp. 761-782."
    ]

    def __init__(self, window: int = 20, k: float = 2.0) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        if k <= 0:
            raise ValueError("k must be > 0")
        self.window = window
        self.k = k

    @property
    def parameters(self) -> dict[str, object]:
        return {"window": self.window, "k": self.k}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        mean = close.rolling(self.window).mean()
        std = close.rolling(self.window).std()
        z_score = (close - mean) / std
        signals = (-(z_score / self.k)).clip(-1.0, 1.0)
        return signals.fillna(0.0)
