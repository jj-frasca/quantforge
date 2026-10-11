"""Model parameters are original evidence even on short sources (ADR-235)."""

from fractions import Fraction

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.calibration import filtered_deviation


@pytest.mark.parametrize("parameter", ["rho", "level_vol", "deviation_vol", "drift"])
@pytest.mark.parametrize(
    "bad", [True, False, np.bool_(True), np.nan, np.inf, -np.inf, "0.01", 0.01j]
)
@pytest.mark.parametrize("n", [0, 1, 5])
def test_filter_invalid_original_scalar_cannot_obtain_estimates(
    parameter: str, bad: object, n: int
) -> None:
    kwargs = {"rho": 0.5, "level_vol": 0.01, "deviation_vol": 0.02, "drift": 0.0003}
    kwargs[parameter] = bad
    with pytest.raises(ValueError, match=r"finite.*numbers"):
        filtered_deviation(np.arange(n, dtype=float), **kwargs)


@pytest.mark.parametrize("rho", [-0.5, 0.0, 0.5])
@pytest.mark.parametrize("drift", [-0.0003, 0.0, 0.0003])
@pytest.mark.parametrize("level_vol", [0.0, 0.01])
def test_filter_valid_signed_parameters_and_zero_level_noise_are_preserved(
    rho: float, drift: float, level_vol: float
) -> None:
    actual = filtered_deviation(
        np.array([-1.0, -0.8, -0.9, -0.7, -0.6]),
        rho=rho,
        level_vol=level_vol,
        deviation_vol=0.02,
        drift=drift,
    )
    assert np.isnan(actual[0])
    assert np.isfinite(actual[1:]).all()


@pytest.mark.parametrize("dtype", [float, np.float16, np.float32, np.float64])
def test_filter_valid_numpy_parameters_keep_native_scalar_operands(dtype: type) -> None:
    actual = filtered_deviation(
        np.zeros(5),
        rho=dtype(0.5),
        level_vol=dtype(0.01),
        deviation_vol=dtype(0.02),
        drift=dtype(0.0),
    )
    np.testing.assert_array_equal(actual, [np.nan, 0.0, 0.0, 0.0, 0.0])


@pytest.mark.parametrize("parameter", ["level_vol", "deviation_vol"])
def test_filter_exact_negative_range_comparison_is_not_replaced_with_float(parameter: str) -> None:
    kwargs = {"rho": 0.5, "level_vol": 0.01, "deviation_vol": 0.02, "drift": 0.0003}
    kwargs[parameter] = Fraction(-1, 10**400)
    with pytest.raises(ValueError, match="level_vol must be >= 0 and deviation_vol > 0"):
        filtered_deviation(np.zeros(1), **kwargs)


@pytest.mark.parametrize("rho", [-1.0, 1.0])
def test_filter_original_stationarity_error_still_precedes_source(rho: float) -> None:
    with pytest.raises(ValueError, match="rho must be in"):
        filtered_deviation(np.array([np.nan]), rho=rho, level_vol=0.01, deviation_vol=0.02)


@pytest.mark.parametrize(("level", "deviation"), [(-0.01, 0.02), (0.01, 0.0)])
def test_filter_original_volatility_range_error_still_precedes_source(
    level: float, deviation: float
) -> None:
    with pytest.raises(ValueError, match="level_vol must be >= 0 and deviation_vol > 0"):
        filtered_deviation(np.array([np.nan]), rho=0.5, level_vol=level, deviation_vol=deviation)


def test_filter_original_drift_validity_precedes_source() -> None:
    with pytest.raises(ValueError, match=r"finite.*numbers"):
        filtered_deviation(
            np.array([np.nan]), rho=0.5, level_vol=0.01, deviation_vol=0.02, drift=np.nan
        )


@given(st.sampled_from(["rho", "level_vol", "deviation_vol", "drift"]), st.booleans())
def test_filter_boolean_model_evidence_is_never_a_numeric_parameter(
    parameter: str, value: bool
) -> None:
    kwargs = {"rho": 0.5, "level_vol": 0.01, "deviation_vol": 0.02, "drift": 0.0003}
    kwargs[parameter] = value
    with pytest.raises(ValueError, match="finite real nonboolean numbers"):
        filtered_deviation(np.zeros(1), **kwargs)
