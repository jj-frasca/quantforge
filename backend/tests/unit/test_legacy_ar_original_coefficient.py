"""Original AR coefficient evidence must precede multiplication (ADR-240)."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.calibration import oracle_sharpe


def _frame(n=4, *, flat=False):
    prices = [100.0] * n if flat else [100.0, 101.0, 100.0, 102.0][:n]
    return pd.DataFrame({"close": np.array(prices, dtype=float)})


@pytest.mark.parametrize("phi", [True, False, np.bool_(True), np.nan, np.inf, -np.inf, "0.5", 0.5j])
@pytest.mark.parametrize("n", [0, 1, 4])
def test_legacy_ar_invalid_original_phi_refuses_before_reference_score(phi, n):
    with pytest.raises(ValueError, match=r"finite.*numbers"):
        oracle_sharpe(_frame(n), phi=phi)


@pytest.mark.parametrize("phi", [np.inf, -np.inf])
def test_legacy_ar_infinite_original_phi_refuses_on_flat_prices(phi):
    with pytest.raises(ValueError, match=r"finite.*numbers"):
        oracle_sharpe(_frame(3, flat=True), phi=phi)


@pytest.mark.parametrize("phi", [-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0])
@pytest.mark.parametrize("cost", [0.0, 0.001])
def test_legacy_ar_existing_signed_finite_coefficient_domain_preserved(phi, cost):
    actual = oracle_sharpe(_frame(), phi=phi, cost_rate=cost)
    assert np.isfinite(actual)
    if phi == 0:
        assert actual == 0.0
    if cost == 0 and phi != 0:
        assert actual == pytest.approx(-np.sign(phi) * 15.821858251676353, rel=1e-13)


@pytest.mark.parametrize("dtype", [float, np.float16, np.float32, np.float64])
@pytest.mark.parametrize("n", [0, 1, 4])
def test_legacy_ar_valid_native_scalar_and_short_history_preserved(dtype, n):
    actual = oracle_sharpe(_frame(n), phi=dtype(0.3))
    assert np.isfinite(actual)
    if n < 2:
        assert actual == 0.0


def test_legacy_ar_original_phi_error_precedes_invalid_source():
    with pytest.raises(ValueError, match=r"finite.*numbers"):
        oracle_sharpe(pd.DataFrame({"close": [-1.0]}), phi=np.nan)


def test_legacy_ar_valid_phi_retains_source_before_cost_error():
    with pytest.raises(ValueError, match="positive and finite"):
        oracle_sharpe(pd.DataFrame({"close": [-1.0]}), phi=0.5, cost_rate=np.nan)


@given(st.booleans())
def test_legacy_ar_boolean_original_phi_cannot_publish_reference_score(phi):
    with pytest.raises(ValueError, match="finite real nonboolean numbers"):
        oracle_sharpe(_frame(), phi=phi)


@given(st.floats(min_value=0.001, max_value=1000, allow_nan=False, allow_infinity=False))
def test_legacy_ar_positive_coefficient_scale_preserves_sign_reference(phi):
    assert oracle_sharpe(_frame(), phi=phi) == oracle_sharpe(_frame(), phi=0.5)
