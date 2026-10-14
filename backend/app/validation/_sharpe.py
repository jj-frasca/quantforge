"""Certified represented Float64 dispersion for OOS scalar scores (ADR-291)."""

import math

import numpy as np
import numpy.typing as npt

from app.research.backtesting.metrics import TRADING_DAYS


def _certified_float64_sharpe(
    values: npt.NDArray[np.float64], mean: float, native_score: float
) -> float:
    """Retain the accepted numerator; translate only within Sterbenz's exact range.

    Notes:
        Call only after the original nonconstant native moment/score guards.
        Goldberg (1991), Theorem 11 certifies the inclusive factor-two subtraction.
        Normalized differences contain zero and unit magnitude, bounding sample STD.
    """
    with np.errstate(all="ignore"):
        minimum = float(values.min())
        maximum = float(values.max())
        minimum_magnitude = min(abs(minimum), abs(maximum))
        maximum_magnitude = max(abs(minimum), abs(maximum))
        if (
            mean == 0
            or not (minimum > 0 or maximum < 0)
            or maximum_magnitude > 2 * minimum_magnitude
        ):
            return native_score
        differences = values - values[0]
        scale = float(np.max(np.abs(differences)))
        std = float((differences / scale).std(ddof=1))
        mean_mantissa, mean_exponent = math.frexp(mean)
        scale_mantissa, scale_exponent = math.frexp(scale)
        try:
            score = math.ldexp(
                float(np.sqrt(TRADING_DAYS) * mean_mantissa / scale_mantissa / std),
                mean_exponent - scale_exponent,
            )
        except OverflowError as exc:
            raise ValueError(
                "nonconstant returns must have measurable finite Sharpe moments"
            ) from exc
    if not math.isfinite(score):
        raise ValueError("nonconstant returns must have measurable finite Sharpe moments")
    return score
