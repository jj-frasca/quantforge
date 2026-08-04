from typing import ClassVar

import numpy as np
import pandas as pd

from app.research.strategies.base import BaseStrategy


class CoppockCurveStrategy(BaseStrategy):
    """Coppock Curve: long-term momentum via a weighted MA of two summed rate-of-change series.

    Notes:
        Edwin Coppock (1962) summed two rate-of-change measures (percent change over `roc_long` and
        `roc_short` bars) and smoothed them with a linearly-weighted moving average over
        `wma_window` — a slow momentum oscillator built to time major bottoms. Classic (monthly)
        params are 14/11/10. The original rule is long-only (buy when the curve turns up from below
        zero); here it is generalized to a symmetric trend sign: long when the curve is above zero
        (positive long-term momentum), short when below, flat at exactly zero. Every term is a
        trailing `.shift`/rolling window, so the signal at t uses only prices <= t — no look-ahead;
        the warmup rows are NaN and stay flat.
    """

    name: ClassVar[str] = "coppock_curve"
    research_citations: ClassVar[list[str]] = [
        "Coppock, E.S. 'Practical Relative Strength Charting'. Barron's, 1962 (the Coppock Curve)."
    ]

    def __init__(self, roc_long: int = 14, roc_short: int = 11, wma_window: int = 10) -> None:
        if roc_short < 1:
            raise ValueError("roc_short must be >= 1")
        if roc_long <= roc_short:
            raise ValueError("roc_long must be > roc_short")
        if wma_window < 2:
            raise ValueError("wma_window must be >= 2")
        self.roc_long = roc_long
        self.roc_short = roc_short
        self.wma_window = wma_window

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "roc_long": self.roc_long,
            "roc_short": self.roc_short,
            "wma_window": self.wma_window,
        }

    def _wma(self, series: pd.Series) -> pd.Series:
        """Linearly-weighted moving average (weights 1..window, newest heaviest), trailing."""
        weights = np.arange(1, self.wma_window + 1, dtype=float)
        return series.rolling(self.wma_window).apply(
            lambda w: float(np.dot(w, weights) / weights.sum()), raw=True
        )

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        roc_long = close / close.shift(self.roc_long) - 1.0
        roc_short = close / close.shift(self.roc_short) - 1.0
        coppock = self._wma(roc_long + roc_short)

        signals = pd.Series(0.0, index=data.index)
        signals.loc[coppock > 0.0] = 1.0
        signals.loc[coppock < 0.0] = -1.0
        return signals
