"""Annualized sample volatility must retain measured scale (ADR-208)."""

from decimal import Decimal, localcontext

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.backtesting.metrics import BacktestMetrics


def exact_volatility(values) -> Decimal:
    with localcontext() as context:
        context.prec = 800
        observations = [Decimal.from_float(float(value)) for value in values]
        mean = sum(observations) / len(observations)
        variance = sum((value - mean) ** 2 for value in observations) / (len(observations) - 1)
        return Decimal(252).sqrt() * variance.sqrt()


@pytest.mark.parametrize("scale", [1e-160, 1e-200, 1e-300, 1e-320])
@pytest.mark.parametrize("dtype", ["float64", "Float64"])
@pytest.mark.parametrize("error_mode", ["ignore", "raise"])
def test_annualized_volatility_recovers_native_underflow(scale, dtype, error_mode):
    values = np.array([-0.01, 0.02, -0.03, 0.04]) * scale
    returns = pd.Series(values, dtype=dtype)
    with np.errstate(all=error_mode):
        actual = BacktestMetrics.from_series(returns).annualized_vol
    expected = float(exact_volatility(returns))
    # Permit one output ULP when the correct volatility is itself subnormal.
    assert actual == pytest.approx(expected, rel=5e-14, abs=np.nextafter(0.0, 1.0))
    assert actual > 0


@pytest.mark.parametrize("constant", [0.1, 0.3, 0.0, 1e-200])
def test_annualized_volatility_exact_constants_are_zero(constant):
    assert BacktestMetrics.from_series(pd.Series([constant] * 12)).annualized_vol == 0.0


@pytest.mark.parametrize("dtype", ["float32", "Float32", "float64", "Float64"])
def test_annualized_volatility_preserves_measurable_native_result_exactly(dtype):
    returns = pd.Series([-0.013, 0.012, -0.002, 0.011], dtype=dtype)
    expected = float(returns.std() * np.sqrt(252))
    assert BacktestMetrics.from_series(returns).annualized_vol == expected


@settings(deadline=None)
@given(exponent=st.integers(min_value=-300, max_value=-1))
def test_annualized_volatility_representable_scale_matches_exact_sample_oracle(exponent):
    returns = pd.Series(np.array([-0.01, 0.02, -0.03, 0.04]) * 10.0**exponent)
    actual = BacktestMetrics.from_series(returns).annualized_vol
    assert actual == pytest.approx(float(exact_volatility(returns)), rel=5e-14, abs=0)


def test_annualized_volatility_annualizes_before_restoring_subnormal_scale():
    returns = pd.Series([0.0, np.nextafter(0.0, 1.0)])
    expected = float(exact_volatility(returns))
    with np.errstate(all="raise"):
        actual = BacktestMetrics.from_series(returns).annualized_vol
    assert actual == expected
    assert actual > 0


def test_annualized_volatility_genuine_overflow_is_explicitly_unmeasurable():
    from app.research.backtesting import metrics

    returns = pd.Series([-np.finfo(float).max, np.finfo(float).max])
    assert exact_volatility(returns) > Decimal.from_float(np.finfo(float).max)
    with np.errstate(all="raise"), pytest.raises(ValueError, match="volatility"):
        metrics._annualized_volatility(returns)


@pytest.mark.parametrize("returns", [pd.Series([np.nan]), pd.Series([True]), pd.Series(["0"])])
def test_annualized_volatility_helper_validates_before_shortcut(returns):
    from app.research.backtesting import metrics

    with pytest.raises(ValueError):
        metrics._annualized_volatility(returns)
