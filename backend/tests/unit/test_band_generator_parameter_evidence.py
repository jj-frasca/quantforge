"""Original band model evidence must survive generator provenance checks (ADR-237)."""

from fractions import Fraction

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.calibration import mean_reverting_edge


def _parameters():
    return {
        "n_bars": 20,
        "seed": 61,
        "half_life": 5.0,
        "deviation_share": 0.5,
        "total_vol": 0.012,
        "drift": 0.0003,
        "start_price": 100.0,
    }


@pytest.mark.parametrize(
    "parameter", ["half_life", "deviation_share", "total_vol", "drift", "start_price"]
)
@pytest.mark.parametrize("bad", [True, False, np.bool_(True), np.nan, np.inf, -np.inf, "0.5", 0.5j])
@pytest.mark.parametrize("n", [1, 20])
def test_band_generator_invalid_original_model_scalar_refuses(parameter, bad, n):
    kwargs = _parameters()
    kwargs[parameter] = bad
    kwargs["n_bars"] = n
    with pytest.raises(ValueError, match=r"finite.*numbers"):
        mean_reverting_edge(**kwargs)


@pytest.mark.parametrize("dtype", [float, np.float16, np.float32, np.float64])
@pytest.mark.parametrize("share", [0.5, 1.0])
def test_band_generator_valid_native_inputs_preserve_finite_source_and_startup(dtype, share):
    kwargs = _parameters()
    for parameter in ["half_life", "deviation_share", "total_vol", "drift", "start_price"]:
        kwargs[parameter] = dtype(kwargs[parameter])
    kwargs["deviation_share"] = dtype(share)
    edge = mean_reverting_edge(**kwargs)
    assert np.isfinite(edge.frame.to_numpy()).all()
    assert edge.frame.close.gt(0).all()
    assert edge.achievable_conditional_mean.iloc[:2].isna().all()
    assert np.isfinite(edge.achievable_conditional_mean.iloc[2:]).all()


@pytest.mark.parametrize("parameter", ["half_life", "deviation_share"])
def test_band_generator_original_negative_fraction_retains_range_error(parameter):
    kwargs = _parameters()
    kwargs[parameter] = Fraction(-1, 10**400)
    with pytest.raises(ValueError, match=parameter + " must be"):
        mean_reverting_edge(**kwargs)


def test_band_generator_count_error_retains_precedence():
    kwargs = _parameters()
    kwargs.update(n_bars=0, half_life=True)
    with pytest.raises(ValueError, match="n_bars must be"):
        mean_reverting_edge(**kwargs)


@pytest.mark.parametrize(("half_life", "share"), [(0.0, np.nan), (5.0, 0.0)])
def test_band_generator_existing_range_error_retains_precedence(half_life, share):
    kwargs = _parameters()
    kwargs.update(half_life=half_life, deviation_share=share, start_price=np.nan)
    with pytest.raises(
        ValueError, match="half_life must be" if half_life == 0 else "deviation_share must be"
    ):
        mean_reverting_edge(**kwargs)


@given(st.sampled_from(["half_life", "deviation_share", "total_vol", "start_price"]), st.booleans())
def test_band_generator_boolean_model_provenance_cannot_publish_source(parameter, value):
    kwargs = _parameters()
    kwargs[parameter] = value
    with pytest.raises(ValueError, match="finite real nonboolean numbers"):
        mean_reverting_edge(**kwargs)


@pytest.mark.parametrize("drift", [-0.001, 0.0])
def test_band_generator_valid_signed_drift_preserves_measured_forecast(drift):
    kwargs = _parameters()
    kwargs["drift"] = drift
    edge = mean_reverting_edge(**kwargs)
    assert np.isfinite(edge.frame.to_numpy()).all()
    assert np.isfinite(edge.achievable_conditional_mean.iloc[2:]).all()
