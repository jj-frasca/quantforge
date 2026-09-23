from dataclasses import dataclass
from typing import Literal, cast

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.stats import norm

TRADING_DAYS = 252
_MIN_YEARS_FOR_SHARPE_CI = 1.0


def sharpe_ratio(returns: pd.Series) -> float:
    """Annualized Sharpe (sqrt(252)); 0.0 for a constant/degenerate return series."""
    if len(returns) < 2:
        return 0.0
    std = float(returns.std())
    if std == 0.0 or not np.isfinite(std):
        return 0.0
    return float(np.sqrt(TRADING_DAYS) * returns.mean() / std)


@dataclass(frozen=True)
class SharpeConfidenceInterval:
    """An iid-normal confidence interval around an observed annualized Sharpe."""

    assumption: Literal["iid_normal"]
    confidence: float
    lower: float
    upper: float


def sharpe_confidence_interval(
    returns: pd.Series, *, confidence: float = 0.95
) -> SharpeConfidenceInterval | None:
    """Confidence interval on the annualized Sharpe via Lo (2002)'s asymptotic standard error.

    Notes:
        Answers a different question than PBO/DSR: those price MULTIPLE-TESTING/selection bias
        across a search; this is the SAMPLING uncertainty in one already-observed Sharpe, given
        only the years of history actually available. Standard error is
        `sqrt((1 + SR^2 / (2*252)) / years)` — the same asymptotic formula this project already
        uses for the detectable-edge frontier (ADR-043, `app/research/lab/frontier.py`'s
        `sharpe_standard_error`), re-derived here rather than imported: `backtesting/` sits below
        `lab/` in this codebase's layering, so a function here cannot import from there.
        `None` when there are fewer than 2 returns (Sharpe itself is undefined) or fewer than a
        year of data, below which the asymptotic normal approximation is unreliable.
    """
    if not np.isfinite(confidence) or not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be finite and between 0 and 1")
    if len(returns) < 2:
        return None
    years = len(returns) / TRADING_DAYS
    if years < _MIN_YEARS_FOR_SHARPE_CI:
        return None
    sharpe = sharpe_ratio(returns)
    standard_error = float(np.sqrt((1.0 + sharpe**2 / (2.0 * TRADING_DAYS)) / years))
    z = float(norm.ppf(0.5 + confidence / 2.0))
    return SharpeConfidenceInterval(
        assumption="iid_normal",
        confidence=confidence,
        lower=sharpe - z * standard_error,
        upper=sharpe + z * standard_error,
    )


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


def calmar_ratio(annualized_return: float, max_drawdown: float) -> float:
    """Annualized return over the magnitude of max drawdown (Young 1991), ADR-108.

    Notes:
        Pure ratio of two already-computed `BacktestMetrics` fields, not a new estimate from
        a returns Series. 0.0 when `max_drawdown == 0.0` (a flat/never-drawn-down equity
        curve), mirroring `sharpe_ratio`/`sortino_ratio`'s degenerate-series convention of
        0.0 rather than +inf.
    """
    if max_drawdown == 0.0:
        return 0.0
    return float(annualized_return / abs(max_drawdown))


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


def _validated_log_returns(returns: pd.Series) -> NDArray[np.float64]:
    values = returns.to_numpy(dtype=np.float64)
    if not np.isfinite(values).all():
        raise ValueError("returns must be finite")
    if np.any(values <= -1.0):
        raise ValueError("returns must preserve positive compounded wealth")
    log_returns = np.log1p(values)
    return cast(NDArray[np.float64], log_returns)


def _compounded_log_growth(returns: pd.Series) -> float:
    with np.errstate(over="ignore", invalid="ignore"):
        return float(_validated_log_returns(returns).sum())


def total_return(returns: pd.Series) -> float:
    """Complete compounded return, including the first net observation (ADR-110)."""
    if len(returns) == 0:
        return 0.0
    with np.errstate(over="ignore", under="ignore"):
        growth = float(np.exp(_compounded_log_growth(returns)))
    if not np.isfinite(growth) or growth <= 0.0:
        raise ValueError("compounded wealth must be positive and finite")
    return growth - 1.0


def annualized_return(returns: pd.Series) -> float:
    """Geometric annual return over the complete net-return path (ADR-110)."""
    if len(returns) == 0:
        return 0.0
    annual_log_growth = _compounded_log_growth(returns) * TRADING_DAYS / len(returns)
    with np.errstate(over="ignore", under="ignore"):
        growth = float(np.exp(annual_log_growth))
    if not np.isfinite(growth) or growth <= 0.0:
        raise ValueError("annualized wealth must be positive and finite")
    return growth - 1.0


def _max_drawdown_from_returns(returns: pd.Series) -> float:
    if len(returns) == 0:
        return 0.0
    cumulative_log_growth = np.cumsum(_validated_log_returns(returns))
    with np.errstate(over="ignore", under="ignore"):
        wealth = np.exp(np.concatenate(([0.0], cumulative_log_growth)))
    if not np.isfinite(wealth).all() or np.any(wealth <= 0.0):
        raise ValueError("compounded wealth path must be positive and finite")
    return max_drawdown(pd.Series(wealth))


@dataclass(frozen=True)
class BacktestMetrics:
    sharpe: float
    max_drawdown: float
    total_return: float
    annualized_return: float
    annualized_vol: float
    sortino: float
    calmar: float
    sharpe_ci: SharpeConfidenceInterval | None

    @classmethod
    def from_series(cls, net_returns: pd.Series) -> "BacktestMetrics":
        ann_return = annualized_return(net_returns)
        dd = _max_drawdown_from_returns(net_returns)
        ann_vol = float(net_returns.std() * np.sqrt(TRADING_DAYS)) if len(net_returns) > 1 else 0.0
        return cls(
            sharpe=sharpe_ratio(net_returns),
            max_drawdown=dd,
            total_return=total_return(net_returns),
            annualized_return=ann_return,
            annualized_vol=ann_vol,
            sortino=sortino_ratio(net_returns),
            calmar=calmar_ratio(annualized_return=ann_return, max_drawdown=dd),
            sharpe_ci=sharpe_confidence_interval(net_returns),
        )
