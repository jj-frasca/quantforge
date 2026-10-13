"""Exact represented-return beta oracles for remaining FINDING-113 scope."""

from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.benchmarks.comparator import BenchmarkComparator


def _oracle(strategy: pd.Series, benchmark: pd.Series) -> float:
    xs = [Fraction.from_float(float(x)) for x in benchmark]
    ys = [Fraction.from_float(float(y)) for y in strategy]
    xm, ym = sum(xs) / len(xs), sum(ys) / len(ys)
    covariance = sum((x - xm) * (y - ym) for x, y in zip(xs, ys, strict=True))
    variance = sum((x - xm) ** 2 for x in xs)
    return float(covariance / variance)


@pytest.mark.parametrize(
    ("benchmark_scale", "strategy_scale"),
    [(2e-162, 1e-162), (3e-162, 1e-162), (1e-160, 1e-170), (1e-100, 1e-230)],
)
@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("dtype", ["float64", "Float64"])
def test_beta_recovers_underflow_with_positive_native_variance(
    benchmark_scale: float, strategy_scale: float, sign: int, dtype: str
) -> None:
    benchmark = pd.Series([i * benchmark_scale for i in (1, 2, 3)], dtype=dtype)
    strategy = pd.Series([sign * i * strategy_scale for i in (1, 2, 3)], dtype=dtype)
    before_strategy, before_benchmark = strategy.copy(deep=True), benchmark.copy(deep=True)
    assert benchmark.var() > 0
    expected = _oracle(strategy, benchmark)
    state = np.geterr()
    with np.errstate(all="ignore"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert np.geterr() == state
    assert result.beta == pytest.approx(expected, rel=1e-12, abs=0)
    pd.testing.assert_series_equal(strategy, before_strategy)
    pd.testing.assert_series_equal(benchmark, before_benchmark)
    pd.testing.assert_series_equal(result.excess_returns, strategy - benchmark)


@pytest.mark.parametrize("scale", [1e-162, 3e-162, 1e-200])
def test_beta_same_series_retains_neutrality_under_strict_numpy_state(scale: float) -> None:
    returns = pd.Series([scale, 2 * scale, 3 * scale])
    with np.errstate(all="raise"):
        state = np.geterr()
        result = BenchmarkComparator().compare(returns, returns)
        assert np.geterr() == state
    assert result.beta == pytest.approx(1, rel=1e-12, abs=0)
    assert result.alpha == 0


@pytest.mark.parametrize("scale", [0.0, 0.125, 1e-162, 1e-200, 1e100])
def test_beta_preserves_true_constant_benchmark_convention(scale: float) -> None:
    result = BenchmarkComparator().compare(pd.Series([0.01, 0.02, 0.03]), pd.Series([scale] * 3))
    assert result.beta == 0


def test_beta_retains_zero_strategy_with_subnormal_variance() -> None:
    result = BenchmarkComparator().compare(
        pd.Series([0.0] * 3), pd.Series([3e-162, 6e-162, 9e-162])
    )
    assert result.beta == 0
    assert result.alpha == 0


@settings(max_examples=80, deadline=None)
@given(
    benchmark_exponent=st.integers(min_value=154, max_value=170),
    strategy_exponent=st.integers(min_value=154, max_value=250),
    sign=st.sampled_from([-1, 1]),
    n=st.integers(min_value=3, max_value=12),
)
def test_beta_tiny_affine_samples_match_exact_represented_input_oracle(
    benchmark_exponent: int, strategy_exponent: int, sign: int, n: int
) -> None:
    benchmark = pd.Series([i * 10.0**-benchmark_exponent for i in range(1, n + 1)])
    strategy = pd.Series([sign * i * 10.0**-strategy_exponent for i in range(1, n + 1)])
    expected = _oracle(strategy, benchmark)
    with np.errstate(all="ignore"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == pytest.approx(expected, rel=1e-12, abs=0)


def test_beta_exact_constant_benchmark_does_not_fabricate_centering_residual() -> None:
    # ADR-269 resolves the separate rounded-centering defect identified during ADR-268.
    result = BenchmarkComparator().compare(pd.Series([0.01, 0.02, 0.03]), pd.Series([0.1] * 3))
    assert result.beta == 0


@pytest.mark.parametrize("exponent", [-520, -540])
def test_beta_preserves_exact_zero_covariance_at_tiny_scale(exponent: int) -> None:
    scale = 2.0**exponent
    benchmark = pd.Series([-scale, 0.0, scale])
    strategy = pd.Series([scale, -2 * scale, scale])
    assert _oracle(strategy, benchmark) == 0
    with np.errstate(all="ignore"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == 0
