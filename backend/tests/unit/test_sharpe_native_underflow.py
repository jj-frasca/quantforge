"""Exact-float evidence for ADR-209's particular native arithmetic failures."""

import math
from decimal import Decimal, localcontext

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st
from scipy.stats import norm

from app.research.backtesting.metrics import sharpe_confidence_interval, sharpe_ratio


def _exact_sample_sharpe(values) -> float:
    with localcontext() as context:
        context.prec = 800
        observations = [Decimal.from_float(float(value)) for value in values]
        mean = sum(observations) / len(observations)
        variance = sum((value - mean) ** 2 for value in observations) / (len(observations) - 1)
        return float(Decimal(252).sqrt() * mean / variance.sqrt())


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
@pytest.mark.parametrize("error_mode", ["ignore", "warn", "raise"])
@pytest.mark.parametrize(
    "values",
    [
        [-1e-161, 2e-161, -3e-161, 4e-161],
        [-1e-160, 1e-160, np.nextafter(0.0, 1.0)],
        [-1e100, 1e-200, 1e100],
        [-1e100, -1e-200, 1e100],
        [-1e200, 1e-100, 1e200],
    ],
)
def test_detected_native_failures_recover_exact_float_sample_sharpe(
    dtype, error_mode, values
) -> None:
    returns = pd.Series(values, dtype=dtype)
    expected = _exact_sample_sharpe(returns)
    assert expected != 0
    with np.errstate(all=error_mode):
        assert sharpe_ratio(returns) == pytest.approx(expected, rel=5e-14, abs=0)


@pytest.mark.parametrize("dtype", ["float32", "Float32"])
def test_narrow_dtype_underflow_recovery_uses_original_float64_observations(dtype) -> None:
    returns = pd.Series(np.array([-1, 2, -3, 4]) * 1e-23, dtype=dtype)
    with np.errstate(all="raise"):
        assert sharpe_ratio(returns) == pytest.approx(
            _exact_sample_sharpe(returns), rel=5e-14, abs=0
        )


@pytest.mark.parametrize("n", [3, 100])
@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("position", [0, 1, 2])
def test_recovered_subnormal_sum_is_annualized_before_sample_count(n, sign, position) -> None:
    values = [-1.0, 1.0]
    values.insert(position, sign * np.nextafter(0.0, 1.0))
    values.extend([0.0] * (n - 3))
    expected = _exact_sample_sharpe(values)
    assert expected * sign > 0
    with np.errstate(all="raise"):
        assert sharpe_ratio(pd.Series(values)) == expected


@given(exponent=st.integers(10, 500), gap=st.integers(55, 950), sign=st.sampled_from([-1, 1]))
def test_representable_cancellation_residual_retains_sign_and_sample_score(
    exponent, gap, sign
) -> None:
    large = math.ldexp(1.0, exponent)
    residual = sign * math.ldexp(1.0, exponent - gap)
    values = [-large, residual, large]
    expected = _exact_sample_sharpe(values)
    assert math.isfinite(expected) and expected * sign > 0
    with np.errstate(all="raise"):
        result = sharpe_ratio(pd.Series(values))
    assert result * sign > 0
    assert result == pytest.approx(expected, rel=5e-14, abs=0)


@pytest.mark.parametrize("dtype", ["float64", "Float64", "float32", "Float32"])
def test_ordinary_native_score_keeps_original_operation_order(dtype) -> None:
    returns = pd.Series([-0.01, 0.02, -0.03, 0.04, 0.01], dtype=dtype)
    expected = float(np.sqrt(252) * float(returns.mean()) / float(returns.std()))
    with np.errstate(all="raise"):
        assert sharpe_ratio(returns) == expected


@pytest.mark.parametrize(
    "values",
    [
        [-0.01, 0.01],
        [-1e-161, 1e-161],
        [-1e308, 1e308],
        [1e308, 1e308, -1e308, -1e308],
        [-1e308, np.nextafter(0.0, 1.0), 1e308],
    ],
)
def test_true_cancellation_or_unrepresentably_tiny_score_remains_zero(values) -> None:
    assert _exact_sample_sharpe(values) == 0
    with np.errstate(all="raise"):
        assert sharpe_ratio(pd.Series(values)) == 0


def test_interval_inherits_corrected_partial_underflow_center() -> None:
    returns = pd.Series([-1e-161, 2e-161, -3e-161, 4e-161] * 63)
    expected = _exact_sample_sharpe(returns)
    width = norm.isf(0.025) * math.sqrt(1 + expected**2 / 504)
    with np.errstate(all="raise"):
        interval = sharpe_confidence_interval(returns)
    assert interval is not None
    assert interval.lower == pytest.approx(expected - width, rel=5e-14, abs=0)
    assert interval.upper == pytest.approx(expected + width, rel=5e-14, abs=0)
