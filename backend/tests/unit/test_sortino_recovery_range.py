"""Exact-float tests for ADR-210 recovery range, separate from native estimators."""

import math
from decimal import Decimal, localcontext

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.backtesting.metrics import sortino_ratio


def _exact_sortino(values) -> float:
    with localcontext() as context:
        context.prec = 800
        observations = [Decimal.from_float(float(value)) for value in values]
        downside_variance = sum(min(value, Decimal(0)) ** 2 for value in observations) / len(
            observations
        )
        return float(
            Decimal(252).sqrt() * (sum(observations) / len(observations)) / downside_variance.sqrt()
        )


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
@pytest.mark.parametrize("error_mode", ["ignore", "raise"])
@pytest.mark.parametrize("n", [3, 100])
@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("position", [0, 1, 2])
def test_subnormal_sum_survives_recovery_sample_count(dtype, error_mode, n, sign, position) -> None:
    values = [-1.0, 1.0]
    values.insert(position, sign * np.nextafter(0.0, 1.0))
    values.extend([0.0] * (n - 3))
    expected = _exact_sortino(values)
    assert expected * sign > 0
    with np.errstate(all=error_mode):
        assert sortino_ratio(pd.Series(values, dtype=dtype)) == expected


@given(
    exponent=st.integers(0, 20),
    gap=st.integers(1000, 1074),
    n=st.integers(3, 128),
    sign=st.sampled_from([-1, 1]),
)
def test_binary_scaled_tiny_residual_matches_exact_full_sample_ratio(
    exponent, gap, n, sign
) -> None:
    large = math.ldexp(1.0, exponent)
    residual = sign * math.ldexp(1.0, exponent - gap)
    values = [-large, residual, large] + [0.0] * (n - 3)
    expected = _exact_sortino(values)
    assert expected * sign > 0
    with np.errstate(all="raise"):
        result = sortino_ratio(pd.Series(values))
    assert result is not None and result * sign > 0
    assert result == pytest.approx(expected, rel=5e-14, abs=0)


@pytest.mark.parametrize("shortfall", [1e-308, 1e-309])
@pytest.mark.parametrize("error_mode", ["ignore", "raise"])
def test_final_range_decides_finite_ratio_or_true_overflow(shortfall, error_mode) -> None:
    values = [-shortfall, 1.0] + [0.0] * 98
    expected = _exact_sortino(values)
    with np.errstate(all=error_mode):
        result = sortino_ratio(pd.Series(values))
    if math.isfinite(expected):
        assert result == pytest.approx(expected, rel=5e-14, abs=0)
    else:
        assert result is None


@pytest.mark.parametrize(
    "values",
    [[-1.0, 1.0], [-1e308, np.nextafter(0.0, 1.0), 1e308], [-1e-160, 1e-160]],
)
def test_genuine_cancellation_or_tiny_score_still_rounds_zero(values) -> None:
    assert _exact_sortino(values) == 0
    with np.errstate(all="raise"):
        assert sortino_ratio(pd.Series(values)) == 0


def test_ordinary_native_score_retains_original_arithmetic() -> None:
    returns = pd.Series([-0.01, 0.02, -0.03, 0.04, 0.01])
    expected = float(np.sqrt(252) * returns.mean() / np.sqrt(np.mean(np.minimum(returns, 0) ** 2)))
    assert sortino_ratio(returns) == expected
