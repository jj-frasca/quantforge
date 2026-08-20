import math

from pydantic import BaseModel, ConfigDict

from app.research.lab.universe import expected_max_sharpe_under_null

# Annualizing Lo (2002)'s per-period SR^2/2 term: SR_annual = sqrt(252) * SR_period, so the term
# becomes SR_annual^2 / (2 * 252).
_ANNUALIZED_SR_SQUARED = 2.0 * 252
# The fixed-point map's derivative is z * SR / (504 * T * SE), which is ~1e-3 at any plausible
# Sharpe, so a fixed iteration count converges past float precision and needs no exit test.
_ITERATIONS = 8


class DetectionFrontier(BaseModel):
    """What an edge must actually BE for this pipeline to detect it (ADR-043).

    Notes:
        `bar` is what must be OBSERVED (ADR-018); `detectable_sharpe` is what must be TRUE for the
        observation to happen with probability `power`. The gap between them is estimation noise,
        which is why an edge sitting exactly at the bar is a coin flip rather than a graduate.

        This is the pipeline's statistical resolution assuming a strategy captures the edge
        perfectly, so it is an OPTIMISTIC bound. ADR-041/042's measured power is the realized
        number; the gap between the two is the catalog's capture efficiency.
    """

    model_config = ConfigDict(frozen=True)

    n_symbols: int
    holdout_years: float
    power: float
    bar: float
    detectable_sharpe: float
    standard_error: float


def sharpe_standard_error(sharpe: float, holdout_years: float) -> float:
    """Standard error of an annualized Sharpe estimated over `holdout_years` of daily data.

    Notes:
        Lo (2002) for iid returns, annualized: sqrt((1 + SR^2 / 504) / T). At SR = 0 this is exactly
        the sqrt(1/T) that `expected_max_sharpe_under_null` uses — the same formula evaluated at the
        null rather than at the alternative. The SR^2 term is what makes a LARGE true Sharpe noisier
        to estimate, which matters precisely at the only effect sizes this pipeline can see.
    """
    if holdout_years <= 0:
        raise ValueError("holdout_years must be > 0")
    return math.sqrt((1.0 + sharpe**2 / _ANNUALIZED_SR_SQUARED) / holdout_years)


def detectable_sharpe(n_symbols: int, holdout_years: float, *, power: float = 0.8) -> float:
    """The smallest TRUE annualized Sharpe the ADR-018 bar clears with probability `power`.

    Notes:
        Solves `SR = bar(N, T) + z_power * SE(SR)`, implicit because the standard error grows with
        the true Sharpe. Fixed-point iteration from the bar; the SR^2 / 504 term makes the map a
        very strong contraction, so a fixed handful of passes lands past float precision.

        Below two symbols the deflation bar is 0.0 (nothing was selected across), but the
        estimation noise does not vanish with it — reporting 0.0 there would claim a coin flip is
        detectable, so the noise term still applies.
    """
    if not 0.0 < power < 1.0:
        raise ValueError("power must be in (0, 1)")
    bar = expected_max_sharpe_under_null(n_symbols, holdout_years)
    z = _normal_quantile(power)
    sharpe = bar
    for _ in range(_ITERATIONS):
        sharpe = bar + z * sharpe_standard_error(sharpe, holdout_years)
    return sharpe


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
    """Inverse standard normal CDF by bisection on `math.erf`.

    Notes:
        Deliberately dependency-free: scipy is not a backend dependency and adding one for a single
        quantile would be a poor trade. Bisection over 200 halvings on [-10, 10] is exact to well
        past float precision and runs in microseconds.
    """
    low, high = -10.0, 10.0
    for _ in range(200):
        mid = (low + high) / 2.0
        if 0.5 * (1.0 + math.erf(mid / math.sqrt(2.0))) < p:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0
