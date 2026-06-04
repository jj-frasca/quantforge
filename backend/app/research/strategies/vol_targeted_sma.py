from typing import ClassVar

import numpy as np
import pandas as pd

from app.research.strategies.base import BaseStrategy


class VolTargetedSMAStrategy(BaseStrategy):
    """SMA crossover with position size inversely scaled by realized volatility.

    Notes:
        This is the first strategy that does **risk management**, not just signal
        generation. The trading direction comes from the same fast/slow SMA crossover
        as `SMAStrategy`, but the position SIZE is `target_vol / realized_vol`, clipped
        to `[0, 1]` so we never lever up. In calm regimes the position approaches the
        full +/-1; in choppy regimes the size shrinks so the strategy maintains an
        approximately constant *portfolio* volatility instead of an asset-volatility
        equal to the underlying's.

        Implementation choices (the "why this code looks like this"):

        - Log returns for the vol estimate. Log returns are time-additive (cleaner
          rolling std), symmetric around 0, and match the academic literature's vol
          definition.
        - Annualized via `sqrt(252)`. The user provides `target_vol` in annualized terms
          ("15% annual"), which is how vol targets are quoted in practice.
        - `clip(upper=1.0)` prevents leverage — the strategy can only de-risk, never
          gear up. (Real-money implementations sometimes gear; we don't here to stay
          honest about a long-only-cash backtest.)
        - Bars before the rolling window fills have NaN vol → `fillna(0.0)` keeps the
          position flat during warmup rather than crashing on NaN.

        Moskowitz, Ooi & Pedersen (2012) show that vol-scaling improves the risk-adjusted
        return of trend-following signals across asset classes; we apply the same principle
        to the simple SMA crossover here.
    """

    name: ClassVar[str] = "vol_targeted_sma"
    research_citations: ClassVar[list[str]] = [
        "Moskowitz, Ooi & Pedersen (2012), 'Time Series Momentum'. "
        "Journal of Financial Economics 104(2), pp. 228-250."
    ]
    _TRADING_DAYS_PER_YEAR = 252

    def __init__(
        self,
        fast: int = 20,
        slow: int = 50,
        vol_window: int = 30,
        target_vol: float = 0.15,
    ) -> None:
        if fast < 1:
            raise ValueError("fast window must be >= 1")
        if fast >= slow:
            raise ValueError("fast window must be < slow window")
        if vol_window < 2:
            raise ValueError("vol_window must be >= 2")
        if target_vol <= 0:
            raise ValueError("target_vol (annualized) must be > 0")
        self.fast = fast
        self.slow = slow
        self.vol_window = vol_window
        self.target_vol = target_vol

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "fast": self.fast,
            "slow": self.slow,
            "vol_window": self.vol_window,
            "target_vol": self.target_vol,
        }

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        fast_ma = close.rolling(self.fast).mean()
        slow_ma = close.rolling(self.slow).mean()

        direction = pd.Series(0.0, index=data.index)
        direction.loc[fast_ma > slow_ma] = 1.0
        direction.loc[fast_ma < slow_ma] = -1.0

        # Annualized realized vol from log returns.
        log_returns = np.log(close / close.shift(1))
        realized_vol = log_returns.rolling(self.vol_window).std() * np.sqrt(
            self._TRADING_DAYS_PER_YEAR
        )

        # Inverse-vol position size, clipped to [0, 1] (no leverage). NaN -> flat.
        with np.errstate(divide="ignore", invalid="ignore"):
            scale = (self.target_vol / realized_vol).clip(upper=1.0).fillna(0.0)

        return (direction * scale).clip(-1.0, 1.0)
