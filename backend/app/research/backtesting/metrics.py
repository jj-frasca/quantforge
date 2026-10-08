from dataclasses import dataclass
from math import fsum
from numbers import Real
from typing import Literal, cast

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype
from scipy.stats import norm

TRADING_DAYS = 252
_MIN_YEARS_FOR_SHARPE_CI = 1.0


def _validate_complete_return_sample(returns: pd.Series) -> None:
    if (
        not is_numeric_dtype(returns.dtype)
        or is_bool_dtype(returns.dtype)
        or is_complex_dtype(returns.dtype)
    ):
        raise ValueError("returns must be real nonboolean numeric observations")
    if not np.isfinite(returns.to_numpy(dtype=float, na_value=np.nan)).all():
        raise ValueError("returns must be finite and complete")


def sharpe_ratio(returns: pd.Series) -> float:
    """Annualized Sharpe of complete real returns; zero for valid degenerate samples."""
    _validate_complete_return_sample(returns)
    if len(returns) < 2 or returns.eq(returns.iloc[0]).all():
        return 0.0
    with np.errstate(over="ignore", under="ignore", invalid="ignore", divide="ignore"):
        std = float(returns.std())
        mean = float(returns.mean())
        if np.isfinite(mean) and np.isfinite(std) and std > 0:
            score = float(np.sqrt(TRADING_DAYS) * mean / std)
            if np.isfinite(score):
                return score
        scale = float(np.max(np.abs(returns.to_numpy(dtype=float, na_value=np.nan))))
        if not np.isfinite(scale) or scale <= 0:
            raise ValueError("nonconstant returns must have measurable finite Sharpe moments")
        normalized = returns / scale
        std = float(normalized.std())
        mean = float(normalized.mean())
        if not np.isfinite(mean) or not np.isfinite(std) or std <= 0:
            raise ValueError("nonconstant returns must have measurable finite Sharpe moments")
        score = float(np.sqrt(TRADING_DAYS) * mean / std)
        if not np.isfinite(score):
            raise ValueError("nonconstant returns must have measurable finite Sharpe moments")
    return score


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
        ADR-183 requires complete finite real numeric observations before those shortcuts;
        missing rows cannot add history or narrow the interval.
    """
    if not np.isfinite(confidence) or not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be finite and between 0 and 1")
    _validate_complete_return_sample(returns)
    if len(returns) < 2:
        return None
    years = len(returns) / TRADING_DAYS
    if years < _MIN_YEARS_FOR_SHARPE_CI:
        return None
    sharpe = sharpe_ratio(returns)
    standard_error = float(np.sqrt((1.0 + sharpe**2 / (2.0 * TRADING_DAYS)) / years))
    # The equivalent upper tail stays representable when the CDF argument rounds to one.
    z = float(norm.isf((1.0 - confidence) / 2.0))
    return SharpeConfidenceInterval(
        assumption="iid_normal",
        confidence=confidence,
        lower=sharpe - z * standard_error,
        upper=sharpe + z * standard_error,
    )


def sortino_ratio(returns: pd.Series, target: float = 0.0) -> float | None:
    """Annualized Sortino ratio (Sortino & van der Meer 1991), ADR-107.

    Notes:
        Divides excess return over `target` by downside semi-deviation instead of total
        standard deviation, so upside dispersion is never charged against the strategy.
        The semi-deviation squares only the shortfall below `target` (returns at or above
        it contribute zero, not a negative penalty) and divides by the FULL sample size,
        not just the count of shortfalls — the original definition. 0.0 when there are
        fewer than two returns or no observation falls below `target` (downside deviation
        0), mirroring `sharpe_ratio`'s degenerate-series convention rather than +inf.
        ADR-205 preserves measurable native scores and recovers failed arithmetic with
        common-scale normalization; an unrepresentable score is None, never invented zero.
        ADR-206 forms nonzero-target excess before averaging and compares float64
        observations, avoiding cancellation and narrow-dtype target rounding. ADR-207
        recovers detected native underflow and zero means with lost original sum evidence.
    """
    target_evidence: object = target
    if isinstance(target_evidence, (bool, np.bool_)) or not isinstance(target_evidence, Real):
        raise ValueError("target must be a finite real nonboolean scalar")
    try:
        target = float(target_evidence)
    except (OverflowError, ValueError) as exc:
        raise ValueError("target must be a finite real nonboolean scalar") from exc
    if not np.isfinite(target):
        raise ValueError("target must be a finite real nonboolean scalar")
    _validate_complete_return_sample(returns)
    if len(returns) < 2:
        return 0.0
    values = returns.to_numpy(dtype=np.float64)
    if not (values < target).any():
        return 0.0
    with np.errstate(over="ignore", under="ignore", invalid="ignore", divide="ignore"):
        excess = values - target
        shortfall = np.minimum(excess, 0.0)
        try:
            # A finite subnormal moment can already have lost precision. Detect
            # native underflow before accepting it; recovery uses normalized data.
            with np.errstate(under="raise"):
                semi_std = float(np.sqrt(np.mean(shortfall**2)))
                # Preserve the original pandas estimator at the default target.
                excess_mean = float(returns.mean() if target == 0 else pd.Series(excess).mean())
                if np.isfinite(semi_std) and semi_std > 0 and np.isfinite(excess_mean):
                    score = float(np.sqrt(TRADING_DAYS) * excess_mean / semi_std)
                    if np.isfinite(score) and (excess_mean != 0 or fsum(excess) == 0):
                        return score
        except (FloatingPointError, OverflowError):
            # fsum overflow also leaves a native zero uncertified.
            pass
        if not np.isfinite(excess).all():
            # Subtract first whenever representable: scaling near-equal source and
            # target separately can erase their exact-float difference.
            source_scale = max(float(np.max(np.abs(values))), abs(target))
            excess = values / source_scale - target / source_scale
        scale = float(np.max(np.abs(excess)))
        if not np.isfinite(scale) or scale <= 0:
            return None
        normalized_excess = excess / scale
        shortfall = np.minimum(normalized_excess, 0.0)
        semi_scale = float(np.max(np.abs(shortfall)))
        if not np.isfinite(semi_scale) or semi_scale <= 0:
            return None
        rms = float(np.sqrt(np.mean((shortfall / semi_scale) ** 2)))
        excess_mean = fsum(normalized_excess) / len(normalized_excess)
        if not np.isfinite(rms) or rms <= 0 or not np.isfinite(excess_mean):
            return None
        score = float((np.sqrt(TRADING_DAYS) * excess_mean / rms) / semi_scale)
    return score if np.isfinite(score) else None


def calmar_ratio(annualized_return: float, max_drawdown: float) -> float:
    """Annualized return over the magnitude of max drawdown (Young 1991), ADR-108.

    Notes:
        Pure ratio of two already-computed `BacktestMetrics` fields, not a new estimate from
        a returns Series. 0.0 when `max_drawdown == 0.0` (a flat/never-drawn-down equity
        curve), mirroring `sharpe_ratio`/`sortino_ratio`'s degenerate-series convention of
        0.0 rather than +inf.
    """
    inputs: tuple[object, object] = (annualized_return, max_drawdown)
    validated: list[float] = []
    for value in inputs:
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
            raise ValueError("Calmar inputs must be finite real nonboolean scalars")
        try:
            scalar = float(value)
        except (OverflowError, ValueError) as exc:
            raise ValueError("Calmar inputs must be finite real nonboolean scalars") from exc
        if not np.isfinite(scalar):
            raise ValueError("Calmar inputs must be finite real nonboolean scalars")
        validated.append(scalar)
    annualized_return, max_drawdown = validated
    if max_drawdown == 0.0:
        return 0.0
    result = float(annualized_return / abs(max_drawdown))
    if not np.isfinite(result):
        raise ValueError("Calmar ratio must be finite")
    return result


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
        ADR-182 rejects incomplete/nonreal source evidence before those shortcuts. Nonfinite
        native higher moments are unmeasured too; missing rows never inflate the PSR count.
    """
    _validate_complete_return_sample(returns)
    if len(returns) < 4 or returns.eq(returns.iloc[0]).all():
        return None
    try:
        with np.errstate(over="ignore", under="raise", invalid="ignore", divide="ignore"):
            std = float(returns.std())
            if std == 0.0 or not np.isfinite(std):
                return None
            skew = float(returns.skew())
            kurtosis = float(returns.kurt()) + 3.0
    except FloatingPointError:
        return None
    if not np.isfinite([skew, kurtosis]).all():
        return None
    return ReturnMoments(
        n_returns=len(returns),
        skew=skew,
        kurtosis=kurtosis,
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
    _validate_complete_return_sample(returns)
    if len(returns) == 0:
        return 0.0
    with np.errstate(over="ignore", under="ignore"):
        growth = float(np.exp(_compounded_log_growth(returns)))
    if not np.isfinite(growth) or growth <= 0.0:
        raise ValueError("compounded wealth must be positive and finite")
    return growth - 1.0


def annualized_return(returns: pd.Series) -> float:
    """Geometric annual return over the complete net-return path (ADR-110)."""
    _validate_complete_return_sample(returns)
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
    sortino: float | None
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
