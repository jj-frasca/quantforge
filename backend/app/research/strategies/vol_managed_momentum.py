from typing import ClassVar

import numpy as np
import pandas as pd

from app.research.strategies.base import BaseStrategy


class VolManagedMomentumStrategy(BaseStrategy):
    """Volatility-managed momentum: a trend sign scaled by inverse realized VARIANCE.

    Notes:
        Moreira & Muir (2017) show that scaling a factor's exposure by the inverse of its
        recent realized VARIANCE (not volatility) raises the factor's risk-adjusted return:
        de-risk after variance spikes, lean in when markets are calm. Here the traded
        direction is the sign of the trailing return over `lookback` bars (time-series
        momentum), and the position SIZE is `target_variance / realized_variance`, clipped
        to [0, 1] so we only ever de-risk, never lever up. `target_variance = target_vol**2`
        with `target_vol` quoted annualized. Realized variance is the annualized variance of
        trailing log returns over `vol_window`. All inputs are trailing / shifted -- no
        look-ahead; a flat (zero-variance) or warmup window leaves the scale at 0 (flat).

        This differs from `vol_targeted_sma` (SMA crossover direction, inverse-VOLATILITY
        scaling) in both the signal and the scaling exponent: inverse-variance is the
        Moreira-Muir prescription and de-risks more aggressively in turbulent regimes.
    """

    name: ClassVar[str] = "vol_managed_momentum"
    research_citations: ClassVar[list[str]] = [
        "Moreira, Alan, and Tyler Muir. 'Volatility-Managed Portfolios'. "
        "Journal of Finance 72, no. 4 (2017), pp. 1611-1644."
    ]
    _TRADING_DAYS_PER_YEAR = 252

    def __init__(
        self,
        lookback: int = 60,
        vol_window: int = 20,
        target_vol: float = 0.15,
    ) -> None:
        if lookback < 1:
            raise ValueError("lookback must be >= 1")
        if vol_window < 2:
            raise ValueError("vol_window must be >= 2")
        if target_vol <= 0.0:
            raise ValueError("target_vol (annualized) must be > 0")
        self.lookback = lookback
        self.vol_window = vol_window
        self.target_vol = target_vol

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "lookback": self.lookback,
            "vol_window": self.vol_window,
            "target_vol": self.target_vol,
        }

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]

        trailing_return = close / close.shift(self.lookback) - 1.0
        direction = pd.Series(0.0, index=data.index)
        direction.loc[trailing_return > 0.0] = 1.0
        direction.loc[trailing_return < 0.0] = -1.0

        log_returns = np.log(close / close.shift(1))
        realized_var = log_returns.rolling(self.vol_window).var() * self._TRADING_DAYS_PER_YEAR
        target_var = self.target_vol**2

        with np.errstate(divide="ignore", invalid="ignore"):
            scale = (target_var / realized_var).clip(upper=1.0).fillna(0.0)

        return (direction * scale).clip(-1.0, 1.0)
