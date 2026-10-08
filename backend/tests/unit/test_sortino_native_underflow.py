"""Native underflow and lost-zero evidence, independently priced (ADR-207)."""

from decimal import Decimal, localcontext
from itertools import permutations

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.backtesting.metrics import sortino_ratio


def decimal_score(values, target=0.0) -> Decimal:
    with localcontext() as context:
        context.prec = 800
        threshold = Decimal.from_float(float(target))
        excess = [Decimal.from_float(float(value)) - threshold for value in values]
        downside = sum(min(value, Decimal(0)) ** 2 for value in excess) / len(excess)
        return Decimal(252).sqrt() * (sum(excess) / len(excess)) / downside.sqrt()


@pytest.mark.parametrize("error_mode", ["ignore", "raise"])
@pytest.mark.parametrize("dtype", ["float64", "Float64"])
def test_sortino_native_mean_underflow_recovers_representable_residual(error_mode, dtype):
    returns = pd.Series([-1e-160, 1e-160, np.nextafter(0.0, 1.0)], dtype=dtype)
    exact = decimal_score(returns)
    assert float(exact) != 0
    with np.errstate(all=error_mode):
        actual = sortino_ratio(returns)
    assert actual == pytest.approx(float(exact), rel=5e-14, abs=0)


@pytest.mark.parametrize("target", [1e-160, 1e-161, 1e-162])
@pytest.mark.parametrize("error_mode", ["ignore", "raise"])
@pytest.mark.parametrize("dtype", ["float64", "Float64"])
def test_sortino_partial_native_downside_square_underflow_recovers(target, error_mode, dtype):
    returns = pd.Series([0.0, 1.0], dtype=dtype)
    with np.errstate(all=error_mode):
        actual = sortino_ratio(returns, target=target)
    assert actual == pytest.approx(float(decimal_score(returns, target)), rel=5e-14, abs=0)


@pytest.mark.parametrize("residual", [1e-200, -1e-200])
@pytest.mark.parametrize("ordering", list(permutations(range(3))))
@pytest.mark.parametrize("error_mode", ["ignore", "raise"])
def test_sortino_original_sum_witness_recovers_lost_zero(residual, ordering, error_mode):
    observations = [-1e100, residual, 1e100]
    returns = pd.Series([observations[index] for index in ordering])
    with np.errstate(all=error_mode):
        actual = sortino_ratio(returns)
    assert actual == pytest.approx(float(decimal_score(returns)), rel=5e-14, abs=0)


@pytest.mark.parametrize("values", [[-1.0, 0.0, 1.0], [-1e-160, 1e-160]])
def test_sortino_genuine_signed_cancellation_remains_measured_zero(values):
    assert decimal_score(values) == 0
    with np.errstate(all="raise"):
        assert sortino_ratio(pd.Series(values)) == 0.0


def test_sortino_tiny_true_ratio_below_float_range_can_remain_measured_zero():
    values = [-1e308, np.nextafter(0.0, 1.0), 1e308]
    exact = decimal_score(values)
    assert exact > 0
    assert float(exact) == 0
    with np.errstate(all="raise"):
        assert sortino_ratio(pd.Series(values)) == 0.0


@settings(deadline=None)
@given(exponent=st.integers(min_value=-100, max_value=100), sign=st.sampled_from([-1, 1]))
def test_sortino_cancellation_residual_scale_matches_exact_float_oracle(exponent, sign):
    peak = 10.0**exponent
    values = [-peak, sign * 1e-200, peak]
    with np.errstate(all="raise"):
        actual = sortino_ratio(pd.Series(values))
    assert actual == pytest.approx(float(decimal_score(values)), rel=5e-14, abs=0)
