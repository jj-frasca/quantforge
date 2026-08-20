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
        )
