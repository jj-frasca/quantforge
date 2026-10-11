"""Native filter arithmetic must remain measurable before producing evidence (ADR-236)."""

from fractions import Fraction

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.calibration import filtered_deviation


@pytest.mark.parametrize("policy", ["ignore", "raise"])
@pytest.mark.parametrize("n", [0, 1, 5])
@pytest.mark.parametrize("scalar", [float, np.float64])
@pytest.mark.parametrize("which", ["level", "deviation"])
def test_filter_overflowed_noise_refuses_before_estimates(policy, n, scalar, which):
    kwargs = {"rho": 0.5, "level_vol": 0.01, "deviation_vol": 0.02}
    kwargs[which + "_vol"] = scalar(1e200)
    with np.errstate(all=policy):
        before = np.geterr().copy()
        with pytest.raises(ValueError, match="filter arithmetic"):
            filtered_deviation(np.log(np.array([100, 101, 100, 101, 100])[:n]), **kwargs)
        assert np.geterr() == before


@pytest.mark.parametrize("policy", ["ignore", "raise"])
@pytest.mark.parametrize("scalar", [float, np.float64])
def test_filter_underflowed_variance_refuses_before_missing_forecast(policy, scalar):
    with np.errstate(all=policy):
        before = np.geterr().copy()
        with pytest.raises(ValueError, match="filter arithmetic"):
            filtered_deviation(
                np.log([100, 101, 100, 101, 100]),
                rho=0.5,
                level_vol=0.0,
                deviation_vol=scalar(1e-200),
            )
        assert np.geterr() == before


@pytest.mark.parametrize("policy", ["ignore", "raise"])
def test_filter_overflowed_finite_innovation_refuses(policy):
    with np.errstate(all=policy), pytest.raises(ValueError, match="filter arithmetic"):
        filtered_deviation(np.array([-1e308, 1e308]), rho=0.5, level_vol=0.01, deviation_vol=0.02)


@pytest.mark.parametrize("rho", [-0.7, 0.0, 0.5])
@pytest.mark.parametrize("level_vol", [0.0, 0.01])
@pytest.mark.parametrize("n", [0, 1, 5])
def test_filter_measurable_signed_semidefinite_recursion_preserved(rho, level_vol, n):
    source = np.log(np.array([100, 101, 100, 101, 100], dtype=float)[:n])
    original = source.copy()
    with np.errstate(all="raise"):
        estimates = filtered_deviation(
            source, rho=rho, level_vol=level_vol, deviation_vol=0.02, drift=-0.001
        )
    assert estimates.shape == source.shape
    assert not np.shares_memory(estimates, source)
    np.testing.assert_array_equal(source, original)
    if n:
        assert np.isnan(estimates[0])
        assert np.isfinite(estimates[1:]).all()


@given(exponent=st.integers(min_value=180, max_value=300))
def test_filter_unmeasurable_covariance_cannot_publish_estimates(exponent):
    with np.errstate(all="ignore"), pytest.raises(ValueError, match="filter arithmetic"):
        filtered_deviation(
            np.log([100, 101, 100]), rho=0.5, level_vol=0.0, deviation_vol=10.0**-exponent
        )


@pytest.mark.parametrize(
    ("scalar", "hex_values"),
    [
        (
            np.float32,
            [
                "0x1.47303fc175c22p-4",
                "0x1.923a27d516ed8p-7",
                "0x1.b648300c2e156p-4",
                "0x1.0ce7036a71b92p-3",
            ],
        ),
        (
            Fraction,
            [
                "0x1.47304039abf33p-4",
                "0x1.923a29c779a70p-7",
                "0x1.b64830833b5a6p-4",
                "0x1.0ce703afb7e92p-3",
            ],
        ),
    ],
)
def test_filter_measurable_original_operands_preserve_native_estimates(scalar, hex_values):
    source = np.array([-1.0, -0.8, -0.9, -0.7, -0.6])
    actual = filtered_deviation(
        source,
        rho=scalar(0.5),
        level_vol=scalar(0.01),
        deviation_vol=scalar(0.02),
        drift=scalar(0.0003),
    )
    assert np.isnan(actual[0])
    np.testing.assert_allclose(
        actual[1:],
        [float.fromhex(x) for x in hex_values],
        rtol=1e-13,
        atol=1e-15,
    )


@pytest.mark.parametrize("policy", ["ignore", "raise"])
def test_filter_finite_innovations_with_overflowed_residual_refuse(policy):
    source = np.array([-1e308, 0.0, 1e308])
    assert np.isfinite(np.diff(source)).all()
    with np.errstate(all=policy), pytest.raises(ValueError, match="filter arithmetic"):
        filtered_deviation(source, rho=-0.9, level_vol=0.0, deviation_vol=0.02)
