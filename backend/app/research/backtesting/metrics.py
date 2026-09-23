from dataclasses import dataclass

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def sharpe_ratio(returns: pd.Series) -> float:
    """Annualized Sharpe (sqrt(252)); 0.0 for a constant/degenerate return series."""
    if len(returns) < 2:
        return 0.0
    std = float(returns.std())
    if std == 0.0 or not np.isfinite(std):
        return 0.0
    return float(np.sqrt(TRADING_DAYS) * returns.mean() / std)


def sortino_ratio(returns: pd.Series, target: float = 0.0) -> float:
    """Annualized Sortino ratio (Sortino & van der Meer 1991), ADR-107.

    Notes:
        Divides excess return over `target` by downside semi-deviation instead of total
        standard deviation, so upside dispersion is never charged against the strategy.
        The semi-deviation squares only the shortfall below `target` (returns at or above
        it contribute zero, not a negative penalty) and divides by the FULL sample size,
        not just the count of shortfalls — the original definition. 0.0 when there are
        fewer than two returns or no observation falls below `target` (downside deviation
        0), mirroring `sharpe_ratio`'s degenerate-series convention rather than +inf.
    """
    if len(returns) < 2:
        return 0.0
    shortfall = np.minimum(returns.to_numpy(dtype=np.float64) - target, 0.0)
    semi_std = float(np.sqrt(np.mean(shortfall**2)))
    if semi_std == 0.0 or not np.isfinite(semi_std):
        return 0.0
    return float(np.sqrt(TRADING_DAYS) * (returns.mean() - target) / semi_std)


@dataclass(frozen=True)
class ReturnMoments:
    """Per-period sample moments of a return series, in the convention the PSR is written in.

    Notes:
        ``kurtosis`` is RAW, not excess: a Normal series reports 3.0, which is what reduces the
        Probabilistic Sharpe Ratio's denominator to the familiar ``1/sqrt(n-1)``. pandas reports
        EXCESS kurtosis, so a caller reading `.kurt()` directly into that formula makes every
        series look three units more Normal than it is (ADR-054).
    """

    n_returns: int
    skew: float
    kurtosis: float


def return_moments(returns: pd.Series) -> ReturnMoments | None:
    """Sample skewness and RAW kurtosis, or None when the series cannot support them.

    Notes:
        Sample kurtosis is undefined below four observations, and pandas reports 0.0 skew and 0.0
        excess kurtosis for a ZERO-VARIANCE series — which would read as a perfectly Normal track
        record rather than as an absent one. Both cases return None so the caller records "not
        measured" instead of a fabricated reading.
    """
    if len(returns) < 4:
        return None
    std = float(returns.std())
    if std == 0.0 or not np.isfinite(std):
        return None
    return ReturnMoments(
        n_returns=len(returns),
        skew=float(returns.skew()),
        kurtosis=float(returns.kurt()) + 3.0,
    )


def max_drawdown(equity: pd.Series) -> float:
    """Largest peak-to-trough drop, clamped to [-1.0, 0.0] (no leverage modelled)."""
    if len(equity) == 0:
        return 0.0
    drawdown = equity / equity.cummax() - 1.0
    return max(float(drawdown.min()), -1.0)


def total_return(equity: pd.Series) -> float:
    if len(equity) == 0:
        return 0.0
    return float(equity.iloc[-1] / equity.iloc[0] - 1.0)


@dataclass(frozen=True)
class BacktestMetrics:
    sharpe: float
    max_drawdown: float
    total_return: float
    annualized_return: float
    annualized_vol: float
    sortino: float

    @classmethod
    def from_series(cls, net_returns: pd.Series, equity: pd.Series) -> "BacktestMetrics":
        ann_return = float(net_returns.mean() * TRADING_DAYS) if len(net_returns) else 0.0
        ann_vol = float(net_returns.std() * np.sqrt(TRADING_DAYS)) if len(net_returns) > 1 else 0.0
        return cls(
            sharpe=sharpe_ratio(net_returns),
            max_drawdown=max_drawdown(equity),
            total_return=total_return(equity),
            annualized_return=ann_return,
            annualized_vol=ann_vol,
            sortino=sortino_ratio(net_returns),
        )
