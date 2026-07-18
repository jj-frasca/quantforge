from typing import ClassVar

import numpy as np
import pandas as pd

from app.research.strategies.base import BaseStrategy


class ResidualMomentumStrategy(BaseStrategy):
    """Residual (idiosyncratic) momentum: momentum of returns AFTER removing the name's own drift.

    Notes:
        Blitz, Huij & Martens (2011) show that momentum computed on the part of returns NOT
        explained by systematic exposure ("residual momentum") is steadier and less crash-prone
        than raw price momentum, because it strips the factor/beta component that drives momentum
        crashes. Without a market series (single-name), we use a self-contained proxy: the residual
        return is the daily return minus its own trailing mean over `mean_window` (the name's recent
        drift). The signal is the sign of the summed residual over `lookback` bars ending `skip` bars
        ago (skip avoids 1-month reversal). Long when recent returns have run ABOVE the name's own
        trend, short below, flat when they track it. All inputs are trailing / shifted -- no
        look-ahead. Documented proxy: this removes own-drift, not a true market beta.
    """

    name: ClassVar[str] = "residual_momentum"
    research_citations: ClassVar[list[str]] = [
        "Blitz, David, Joop Huij, and Martin Martens. 'Residual Momentum'. "
        "Journal of Empirical Finance 18, no. 3 (2011), pp. 506-521."
    ]
    # Deadband so floating-point dust on a (near-)zero residual doesn't trade; real residual
    # momentum sums are orders of magnitude larger.
    _EPS: ClassVar[float] = 1e-9

    def __init__(self, lookback: int = 120, skip: int = 20, mean_window: int = 60) -> None:
        if lookback < 1:
            raise ValueError("lookback must be >= 1")
        if skip < 0:
            raise ValueError("skip must be >= 0")
        if mean_window < 2:
            raise ValueError("mean_window must be >= 2")
        self.lookback = lookback
        self.skip = skip
        self.mean_window = mean_window

    @property
    def parameters(self) -> dict[str, object]:
        return {"lookback": self.lookback, "skip": self.skip, "mean_window": self.mean_window}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        returns = close / close.shift(1) - 1.0
        residual = returns - returns.rolling(self.mean_window).mean()
        residual_momentum = residual.rolling(self.lookback).sum().shift(self.skip)

        signals = pd.Series(0.0, index=data.index)
        signals.loc[residual_momentum > self._EPS] = 1.0
        signals.loc[residual_momentum < -self._EPS] = -1.0
        # A NaN residual momentum (warmup) never trips a threshold -> stays flat.
        return signals.where(~np.isnan(residual_momentum), 0.0)
