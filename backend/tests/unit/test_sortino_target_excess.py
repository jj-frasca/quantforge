"""Exact-float target excess and kernel comparison evidence (ADR-206)."""

from decimal import Decimal, localcontext

import numpy as np
import pandas as pd
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from app.research.backtesting.metrics import sortino_ratio


def exact_sortino(values, target) -> Decimal:
    with localcontext() as context:
        context.prec = 800
        threshold = Decimal.from_float(float(target))
        excess = [Decimal.from_float(float(value)) - threshold for value in values]
        downside = sum(min(value, Decimal(0)) ** 2 for value in excess) / len(excess)
        return Decimal(252).sqrt() * (sum(excess) / len(excess)) / downside.sqrt()


@pytest.mark.parametrize("target", [1.0, -1.0, 1.5e308, -1.5e308])
@pytest.mark.parametrize("upper_steps", [2, 3])
@pytest.mark.parametrize("dtype", ["float64", "Float64"])
@pytest.mark.parametrize("error_mode", ["ignore", "raise"])
def test_sortino_adjacent_target_preserves_exact_excess(target, upper_steps, dtype, error_mode):
    lower = np.nextafter(target, -np.inf)
    upper = target
    for _ in range(upper_steps):
        upper = np.nextafter(upper, np.inf)
    returns = pd.Series([lower, upper], dtype=dtype)
    with np.errstate(all=error_mode):
        actual = sortino_ratio(returns, target=target)
    assert actual == pytest.approx(float(exact_sortino(returns, target)), rel=5e-14, abs=0)


@pytest.mark.parametrize("dtype", ["float32", "Float32"])
@pytest.mark.parametrize("error_mode", ["ignore", "raise"])
def test_sortino_narrow_source_compares_target_in_float64(dtype, error_mode):
    lower = np.float32(0.01)
    target = float(lower) + 1e-12
    returns = pd.Series([lower, np.nextafter(lower, np.float32(np.inf))], dtype=dtype)
    with np.errstate(all=error_mode):
        actual = sortino_ratio(returns, target=target)
    assert actual == pytest.approx(float(exact_sortino(returns, target)), rel=5e-14, abs=0)


@pytest.mark.parametrize("dtype", ["float32", "Float32", "float64", "Float64"])
def test_sortino_zero_target_keeps_measurable_native_estimator_exactly(dtype):
    returns = pd.Series([-0.013, 0.012, -0.002, 0.011], dtype=dtype)
    shortfall = np.minimum(returns.to_numpy(dtype=np.float64), 0.0)
    expected = float(np.sqrt(252) * returns.mean() / np.sqrt(np.mean(shortfall**2)))
    assert sortino_ratio(returns) == expected


@settings(deadline=None)
@given(
    target=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
    # A fixed binary excess grid certifies target arithmetic without asserting
    # precision of independently documented subnormal downside-square moments.
    offsets=st.lists(st.integers(min_value=-1024, max_value=1024), min_size=2, max_size=20),
)
def test_sortino_nonzero_target_matches_full_sample_exact_float_oracle(target, offsets):
    assume(target != 0)
    returns = pd.Series([target + offset / 1024 for offset in offsets])
    assume(bool((returns.to_numpy() < target).any()))
    exact = exact_sortino(returns, target)
    actual = sortino_ratio(returns, target=target)
    if abs(exact) > Decimal.from_float(np.finfo(float).max):
        assert actual is None
    else:
        assert actual == pytest.approx(float(exact), rel=5e-12, abs=5e-12)


def test_sortino_nonzero_target_true_overflow_retains_unmeasured_contract():
    target = np.nextafter(0.0, 1.0)
    returns = pd.Series([0.0, 1.0])
    assert abs(exact_sortino(returns, target)) > Decimal.from_float(np.finfo(float).max)
    assert sortino_ratio(returns, target=target) is None
