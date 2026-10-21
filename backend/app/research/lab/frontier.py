import math
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from numbers import Integral, Real
from statistics import NormalDist

from pydantic import BaseModel, ConfigDict

from app.research.lab.universe import expected_max_sharpe_under_null

# Annualizing Lo (2002)'s per-period SR^2/2 term: SR_annual = sqrt(252) * SR_period, so the term
# becomes SR_annual^2 / (2 * 252).
_ANNUALIZED_SR_SQUARED = 2.0 * 252


class DetectionFrontier(BaseModel):
    """Conditional normal-model Sharpe needed to cross the ADR-018 bar (ADR-292).

    Notes:
        `bar` is what must be OBSERVED (ADR-018); `detectable_sharpe` is what must be TRUE for the
        observation to happen with probability `power`. The gap between them is estimation noise,
        which is why an edge sitting exactly at the bar is a coin flip rather than a graduate.

        This iid asymptotic approximation concerns one bar, not the composite search and
        graduation pipeline. Its gap from measured power does not identify catalog capture
        separately from other model and pipeline differences.
    """

    model_config = ConfigDict(frozen=True)

    n_symbols: int
    holdout_years: float
    power: float
    bar: float
    detectable_sharpe: float
    standard_error: float


def _require_finite_real(value: object, parameter: str) -> None:
    """Inspect original scalar evidence without replacing its native operand."""
    error = f"{parameter} must be a finite real nonboolean scalar"
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(error)
    try:
        finite = math.isfinite(float(value))
    except (OverflowError, ValueError) as exc:
        raise ValueError(error) from exc
    if not finite:
        raise ValueError(error)


def sharpe_standard_error(sharpe: float, holdout_years: float) -> float:
    """Standard error of an annualized Sharpe estimated over `holdout_years` of daily data.

    Notes:
        Lo (2002) for iid returns, annualized: sqrt((1 + SR^2 / 504) / T). At SR = 0 this is exactly
        the sqrt(1/T) that `expected_max_sharpe_under_null` uses — the same formula evaluated at the
        null rather than at the alternative. The SR^2 term is what makes a LARGE true Sharpe noisier
        to estimate, which matters precisely at the only effect sizes this pipeline can see.
        Original finite nonboolean Real evidence is inspected without normalizing operands
        (ADR-334). Integral native squares must retain their exact integer value (ADR-335);
        the final result must remain finite and positive (ADR-336). Finite precision and
        general intermediate integrity remain separate contracts.
    """
    _require_finite_real(holdout_years, "holdout_years")
    if holdout_years <= 0:
        raise ValueError("holdout_years must be > 0")
    _require_finite_real(sharpe, "sharpe")
    square = sharpe**2
    score_evidence: object = sharpe
    square_evidence: object = square
    if isinstance(score_evidence, Integral) and (
        not isinstance(square_evidence, Integral)
        or int(square_evidence) != int(score_evidence) ** 2
    ):
        raise ValueError("integral Sharpe square must retain its exact integer value")
    result = math.sqrt((1.0 + square / _ANNUALIZED_SR_SQUARED) / holdout_years)
    if not math.isfinite(result) or result <= 0:
        raise ValueError("Sharpe standard error must be finite and positive")
    return result


def detectable_sharpe(n_symbols: int, holdout_years: float, *, power: float = 0.8) -> float:
    """Unique signed annualized Sharpe for conditional single-bar power (ADR-292).

    Notes:
        Solves `SR = bar(N, T) + z_power * SE(SR)` only in the open unique inverse regime
        `abs(z_power) < sqrt(504*T)`. Exact represented coefficients certify that domain;
        private Decimal arithmetic and a rationalized negative-quantile branch avoid loss
        near its boundary and near zero. Other regimes raise rather than choosing a branch.

        Below two symbols the deflation bar is 0.0 (nothing was selected across), but the
        estimation noise does not vanish with it — reporting 0.0 there would claim a coin flip is
        detectable, so the noise term still applies.
    """
    if not math.isfinite(holdout_years) or holdout_years <= 0.0:
        raise ValueError("holdout_years must be finite and > 0")
    z = _normal_quantile(power)
    bar = expected_max_sharpe_under_null(n_symbols, holdout_years)
    if not math.isfinite(bar):
        raise ValueError("frontier bar must be finite")
    b = Fraction.from_float(float(bar))
    t = Fraction.from_float(float(holdout_years))
    q = Fraction.from_float(z)
    a = 1 - q * q / (504 * t)
    if a <= 0:
        raise ValueError("requested power is outside the supported unique inverse regime")
    if z == 0.0:
        result = bar
    else:
        c = b * b - q * q / t
        discriminant = b * b - a * c
        with localcontext(Context(prec=160, rounding=ROUND_HALF_EVEN)):

            def d(value: Fraction) -> Decimal:
                return Decimal(value.numerator) / Decimal(value.denominator)

            root = d(discriminant).sqrt()
            candidate = (d(b) + root) / d(a) if z > 0 else d(c) / (d(b) + root)
            result = float(candidate)
    if not math.isfinite(result):
        raise ValueError("frontier root must be finite")
    # This shared function also serves calibration references; retain its arithmetic
    # and refuse a reporting result whose required standard error cannot be represented.
    try:
        se = sharpe_standard_error(result, holdout_years)
    except (OverflowError, ValueError) as exc:
        raise ValueError("frontier standard_error cannot be represented") from exc
    if not math.isfinite(se):
        raise ValueError("frontier standard_error must be finite")
    return result


def describe_frontier(
    n_symbols: int, holdout_years: float, *, power: float = 0.8
) -> DetectionFrontier:
    """The bar and the edge that clears it, reported together — see `DetectionFrontier`."""
    detectable = detectable_sharpe(n_symbols, holdout_years, power=power)
    return DetectionFrontier(
        n_symbols=n_symbols,
        holdout_years=holdout_years,
        power=power,
        bar=expected_max_sharpe_under_null(n_symbols, holdout_years),
        detectable_sharpe=detectable,
        standard_error=sharpe_standard_error(detectable, holdout_years),
    )


def _normal_quantile(p: float) -> float:
    """Tail-safe standard-library inverse normal CDF without forming `1-p`."""
    if not math.isfinite(p) or not 0.0 < p < 1.0:
        raise ValueError("power must be finite and in (0, 1)")
    z = NormalDist().inv_cdf(p)
    if not math.isfinite(z):
        raise ValueError("power quantile must be finite")
    return z
