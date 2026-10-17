"""Known-start, zero-initialized band-price posterior (ADR-310).

This additive binary64 method conditions on every supplied log price. It neither
infers the supplied source law nor replaces historical calibration references.
"""

import math
from numbers import Real
from typing import NamedTuple

import numpy as np
import numpy.typing as npt


class BandPricePosterior(NamedTuple):
    """Deviation mean and variance at index i conditional on log prices through i."""

    deviation_mean: npt.NDArray[np.float64]
    deviation_variance: npt.NDArray[np.float64]


def _finite_real(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real nonboolean scalar")
    try:
        normalized = float(value)
    except (OverflowError, ValueError, TypeError) as exc:
        raise ValueError(f"{name} must be finite and float-representable") from exc
    if not math.isfinite(normalized):
        raise ValueError(f"{name} must be finite and float-representable")
    return normalized


def _measurable(*values: float) -> None:
    if not all(math.isfinite(value) for value in values):
        raise ValueError("posterior arithmetic must remain finite and measurable")


def band_price_posterior(
    log_prices: npt.NDArray[np.generic],
    *,
    rho: float,
    level_vol: float,
    deviation_vol: float,
    drift: float,
    start_price: float,
) -> BandPricePosterior:
    """Condition the explicit Gaussian band law on all observed log prices.

    Notes:
        The pre-shock level and deviation are zero; start_price is the known
        pre-shock scale, not the first observed close. Inputs and calculations
        are explicitly normalized to binary64. Fixed unmeasurable intermediates
        refuse without numerical repair. Finite results do not certify universal
        conditioning accuracy, source correspondence or strategy optimality.
    """
    coefficient = _finite_real(rho, "rho")
    level = _finite_real(level_vol, "level_vol")
    deviation = _finite_real(deviation_vol, "deviation_vol")
    drift_value = _finite_real(drift, "drift")
    start = _finite_real(start_price, "start_price")
    if not (-1 < rho < 1 and -1 < coefficient < 1):
        raise ValueError("rho must be stationary in (-1, 1)")
    if level_vol < 0 or level < 0 or (level_vol > 0 and level == 0):
        raise ValueError("level_vol must be nonnegative without positive-noise underflow")
    if deviation_vol <= 0 or deviation <= 0:
        raise ValueError("deviation_vol must be positive")
    if start_price <= 0 or start <= 0:
        raise ValueError("start_price must be positive")

    if not isinstance(log_prices, np.ndarray):
        raise ValueError("log_prices must be an original NumPy ndarray")
    if log_prices.ndim != 1 or log_prices.dtype.kind not in "iuf":
        raise ValueError("log_prices must be one-dimensional real nonboolean numeric observations")
    if np.ma.isMaskedArray(log_prices) and np.any(np.ma.getmaskarray(log_prices)):
        raise ValueError("log_prices must be complete and finite")
    original = np.asarray(log_prices)
    if not np.isfinite(original).all():
        raise ValueError("log_prices must be complete and finite")

    try:
        with np.errstate(all="ignore"):
            observations = np.array(original, dtype=np.float64, copy=True)
            if not np.isfinite(observations).all():
                raise ValueError("normalized log_prices must be finite")
            coefficient_square = coefficient * coefficient
            deviation_variance = deviation * deviation
            q = deviation_variance * (1.0 - coefficient_square)
            noise = level * level
            log_start = math.log(start)
            initial_variance = q + noise
            _measurable(
                coefficient_square, deviation_variance, q, noise, log_start, initial_variance
            )
            if deviation_variance <= 0 or q <= 0 or initial_variance <= 0:
                raise ValueError("posterior law requires positive measurable innovation variance")
            if level_vol > 0 and noise <= 0:
                raise ValueError("positive level noise must not underflow")
            initial_numerator = q * noise
            variance = initial_numerator / initial_variance
            _measurable(initial_numerator, variance)
            if variance < 0 or (noise > 0 and variance <= 0):
                raise ValueError("positive-noise posterior variance must remain positive")

            means = np.empty(len(observations), dtype=np.float64)
            variances = np.empty(len(observations), dtype=np.float64)
            if not len(observations):
                return BandPricePosterior(means, variances)

            first_difference = float(observations[0]) - log_start
            innovation = first_difference - drift_value
            initial_gain = q / initial_variance
            mean = initial_gain * innovation
            _measurable(first_difference, innovation, initial_gain, mean)
            means[0], variances[0] = mean, variance
            delta = coefficient - 1.0
            delta_square = delta * delta
            _measurable(delta, delta_square)
            for index in range(1, len(observations)):
                difference = float(observations[index]) - float(observations[index - 1])
                z = difference - drift_value
                residual_component = delta_square * variance
                residual_partial = residual_component + q
                residual_variance = residual_partial + noise
                covariance_component = coefficient * delta
                covariance_product = covariance_component * variance
                covariance = covariance_product + q
                predicted_increment = delta * mean
                residual = z - predicted_increment
                predicted_mean = coefficient * mean
                _measurable(
                    difference,
                    z,
                    residual_component,
                    residual_partial,
                    residual_variance,
                    covariance_component,
                    covariance_product,
                    covariance,
                    predicted_increment,
                    residual,
                    predicted_mean,
                )
                if residual_variance <= 0:
                    raise ValueError("posterior requires positive residual variance")
                gain = covariance / residual_variance
                correction = gain * residual
                new_mean = predicted_mean + correction
                variance_sum = variance + noise
                variance_left = q * variance_sum
                variance_right_first = coefficient * coefficient
                variance_right_second = variance_right_first * variance
                variance_right = variance_right_second * noise
                numerator = variance_left + variance_right
                new_variance = numerator / residual_variance
                _measurable(
                    gain,
                    correction,
                    new_mean,
                    variance_sum,
                    variance_left,
                    variance_right_first,
                    variance_right_second,
                    variance_right,
                    numerator,
                    new_variance,
                )
                if new_variance < 0 or (noise > 0 and new_variance <= 0):
                    raise ValueError("positive-noise posterior variance must remain positive")
                mean, variance = new_mean, new_variance
                means[index], variances[index] = mean, variance
            return BandPricePosterior(means, variances)
    except (OverflowError, FloatingPointError, ZeroDivisionError) as exc:
        raise ValueError("posterior arithmetic must remain finite and measurable") from exc
