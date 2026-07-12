from typing import ClassVar

import numpy as np
import pandas as pd

from app.research.strategies.base import BaseStrategy


class CCIStrategy(BaseStrategy):
    """Commodity Channel Index, traded as mean reversion: long when oversold, short when overbought.

    Notes:
        Typical price TP = (high + low + close) / 3. CCI = (TP - SMA(TP)) / (0.015 * MAD),
        where MAD is the mean absolute deviation of TP from its rolling mean over `window`
        and 0.015 is Lambert's scaling constant (so ~70-80% of values fall in [-100, 100]).
        A large positive CCI means TP is far above its recent mean (overbought → short); a
        large negative CCI means far below (oversold → long). We trade the ±`threshold`
        crossings (default 100), flat between. Rolling stats are trailing (no look-ahead).
        Degenerate case: a constant TP gives MAD == 0 → CCI undefined; the NaN never trips
        a threshold, so we stay flat.
    """

    name: ClassVar[str] = "cci"
    research_citations: ClassVar[list[str]] = [
        "Lambert, Donald R. 'Commodity Channel Index: Tools for Trading Cyclic Trends'. "
        "Commodities magazine, 1980."
    ]

    def __init__(self, window: int = 20, threshold: float = 100.0) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        if threshold <= 0:
            raise ValueError("threshold must be > 0")
        self.window = window
        self.threshold = threshold

    @property
    def parameters(self) -> dict[str, object]:
        return {"window": self.window, "threshold": self.threshold}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        typical_price = (data["high"] + data["low"] + data["close"]) / 3.0
        sma = typical_price.rolling(self.window).mean()
        mean_abs_dev = typical_price.rolling(self.window).apply(
            lambda window_vals: np.abs(window_vals - window_vals.mean()).mean(), raw=True
        )
        with np.errstate(divide="ignore", invalid="ignore"):
            cci = (typical_price - sma) / (0.015 * mean_abs_dev)

        signals = pd.Series(0.0, index=data.index)
        signals.loc[cci < -self.threshold] = 1.0
        signals.loc[cci > self.threshold] = -1.0
        return signals
