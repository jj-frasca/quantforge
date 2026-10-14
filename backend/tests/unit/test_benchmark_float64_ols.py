"""Exact represented Float64 OLS coefficients, independently centered Fraction oracle."""

import math
from fractions import Fraction
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from app.research.benchmarks import comparator
from app.research.benchmarks.comparator import BenchmarkComparator

_DTYPES = ["float64", "Float64"]


def _oracle(strategy: pd.Series, benchmark: pd.Series) -> tuple[float, float]:
    a = [Fraction(*value.as_integer_ratio()) for value in strategy]
    b = [Fraction(*value.as_integer_ratio()) for value in benchmark]
    mean_a, mean_b = sum(a) / len(a), sum(b) / len(b)
    beta = Fraction(0)
    if len(set(a)) != 1 and len(set(b)) != 1:
        beta = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b, strict=True)) / sum(
            (y - mean_b) ** 2 for y in b
        )
    return float(beta), float(252 * (mean_a - beta * mean_b))


@pytest.mark.parametrize("strategy_dtype", _DTYPES)
@pytest.mark.parametrize("benchmark_dtype", _DTYPES)
@pytest.mark.parametrize("n", [3, 4, 7, 16])
@pytest.mark.parametrize("base", [0.1, 1.0, float(2**60)])
@pytest.mark.parametrize("slope", [1, 2])
def test_float64_ols_retains_large_origin_and_ulp_intercept(
    strategy_dtype: str, benchmark_dtype: str, n: int, base: float, slope: int
) -> None:
    step = math.ulp(base)
    values = base + np.arange(n) * step
    strategy = pd.Series(slope * values + slope * step, dtype=strategy_dtype, name="r")
    benchmark = pd.Series(values, dtype=benchmark_dtype, name="r")
    expected = _oracle(strategy, benchmark)
    assert expected == (float(slope), 252 * slope * step)
    before_s, before_b = strategy.copy(deep=True), benchmark.copy(deep=True)
    with np.errstate(all="raise"):
        state = np.geterr()
        result = BenchmarkComparator().compare(strategy, benchmark)
        assert np.geterr() == state
    assert (result.beta, result.alpha) == expected
    pd.testing.assert_series_equal(result.excess_returns, strategy - benchmark)
    pd.testing.assert_series_equal(strategy, before_s)
    pd.testing.assert_series_equal(benchmark, before_b)


@pytest.mark.parametrize("strategy_dtype", _DTYPES)
@pytest.mark.parametrize("benchmark_dtype", _DTYPES)
@pytest.mark.parametrize("side", ["strategy", "benchmark", "both"])
def test_float64_ols_constants_use_only_exact_strategy_mean(
    strategy_dtype: str, benchmark_dtype: str, side: str
) -> None:
    strategy = pd.Series(
        [0.1] * 3 if side != "benchmark" else [0.1, 0.2, 0.3], dtype=strategy_dtype
    )
    benchmark = pd.Series(
        [0.1] * 3 if side != "strategy" else [0.1, 0.2, 0.3], dtype=benchmark_dtype
    )
    with patch.object(pd.Series, "cov", side_effect=AssertionError("unused covariance")):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert (result.beta, result.alpha) == _oracle(strategy, benchmark)


@pytest.mark.parametrize("strategy_dtype", _DTYPES)
@pytest.mark.parametrize("benchmark_dtype", _DTYPES)
@pytest.mark.parametrize("scale", [1e-200, 1e-100, 1.0, 1e100])
def test_float64_ols_uneven_cancellation_matches_fraction(
    strategy_dtype: str, benchmark_dtype: str, scale: float
) -> None:
    strategy = pd.Series(np.array([0, 1, 0, 3, 7]) * scale, dtype=strategy_dtype)
    benchmark = pd.Series(np.array([0, 1, 2, 3, 4]) * scale, dtype=benchmark_dtype)
    # Other tiny comparator statistics retain their independent strict-state limitations.
    with np.errstate(all="ignore"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert (result.beta, result.alpha) == _oracle(strategy, benchmark)


@pytest.mark.parametrize("strategy_dtype", _DTYPES)
@pytest.mark.parametrize("benchmark_dtype", _DTYPES)
@pytest.mark.parametrize(
    "case",
    ["full_width", "zero_slope", "subnormal_slope", "half_subnormal_slope", "zero_intercept"],
)
def test_float64_ols_full_width_helper_matches_exact_final_rounding(
    strategy_dtype: str, benchmark_dtype: str, case: str
) -> None:
    tiny = math.ulp(0.0)
    maximum = np.finfo(float).max
    pairs = {
        "full_width": ([maximum, tiny, 0], [maximum, tiny, 0]),
        "zero_slope": ([1, 0, 1], [0, 1, 2]),
        "subnormal_slope": ([0, tiny], [0, 1]),
        "half_subnormal_slope": ([0, tiny], [0, 2]),
        "zero_intercept": ([0, 1, 2], [0, 3, 6]),
    }
    a, b = pairs[case]
    strategy, benchmark = pd.Series(a, dtype=strategy_dtype), pd.Series(b, dtype=benchmark_dtype)
    with np.errstate(all="raise"):
        state = np.geterr()
        actual = comparator._exact_float64_ols(strategy, benchmark, constant_source=False)
        assert np.geterr() == state
    assert actual == _oracle(strategy, benchmark)


@pytest.mark.parametrize("strategy_dtype", _DTYPES)
@pytest.mark.parametrize("benchmark_dtype", _DTYPES)
@pytest.mark.parametrize("case", ["slope", "intercept"])
def test_float64_ols_refuses_unrepresentable_final_coefficients(
    strategy_dtype: str, benchmark_dtype: str, case: str
) -> None:
    strategy = pd.Series([0, np.finfo(float).max], dtype=strategy_dtype)
    benchmark = pd.Series([0, math.ulp(0.0)], dtype=benchmark_dtype)
    if case == "intercept":
        strategy[:] = np.finfo(float).max
        benchmark[:] = 0
    with pytest.raises(OverflowError):
        _oracle(strategy, benchmark)
    with pytest.raises(ValueError, match=r"coefficients.*finite"):
        comparator._exact_float64_ols(strategy, benchmark, constant_source=case == "intercept")
    with pytest.raises(ValueError):
        BenchmarkComparator().compare(strategy, benchmark)


@pytest.mark.parametrize("dtype", _DTYPES)
def test_float64_ols_preserves_alignment_metadata_and_source_refusals(dtype: str) -> None:
    strategy = pd.Series([np.nan, 0.1, 0.2, 0.3], index=[0, 1, 2, 3], dtype=dtype, name="a")
    benchmark = pd.Series([0.2, 0.3, 0.4, np.nan], index=[1, 2, 3, 4], dtype=dtype, name="b")
    a, b = strategy.align(benchmark, join="inner")
    result = BenchmarkComparator().compare(strategy, benchmark)
    assert (result.beta, result.alpha) == _oracle(a, b)
    pd.testing.assert_series_equal(result.excess_returns, a - b)
    for invalid in [np.nan, np.inf, -1.0]:
        bad = strategy.copy()
        bad.iloc[2] = invalid
        with pytest.raises(ValueError, match=r"finite|wealth"):
            BenchmarkComparator().compare(bad, benchmark)
    with pytest.raises(ValueError, match="at least two"):
        BenchmarkComparator().compare(a.iloc[:1], b.iloc[:1])


@settings(max_examples=100, deadline=None)
@example(strategy_dtype="float64", benchmark_dtype="Float64", exponent=60, n=4, slope=1, offset=1)
@given(
    strategy_dtype=st.sampled_from(_DTYPES),
    benchmark_dtype=st.sampled_from(_DTYPES),
    exponent=st.integers(-20, 80),
    n=st.integers(3, 16),
    slope=st.integers(1, 3),
    offset=st.integers(-3, 3),
)
def test_float64_ols_property_uses_original_unrounded_coefficients(
    strategy_dtype: str, benchmark_dtype: str, exponent: int, n: int, slope: int, offset: int
) -> None:
    base = math.ldexp(1.0, exponent)
    values = base + np.arange(n) * math.ulp(base)
    strategy = pd.Series(slope * values + offset * math.ulp(base), dtype=strategy_dtype)
    benchmark = pd.Series(values, dtype=benchmark_dtype)
    assert not strategy.eq(strategy.iloc[0]).all()
    assert not benchmark.eq(benchmark.iloc[0]).all()
    with np.errstate(all="raise"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert (result.beta, result.alpha) == _oracle(strategy, benchmark)


@pytest.mark.parametrize(
    "other", ["float16", "float32", "Float32", "int64", "Int64", "uint64", "UInt64", np.longdouble]
)
@pytest.mark.parametrize("dtype", _DTYPES)
@pytest.mark.parametrize("side", ["strategy", "benchmark"])
def test_float64_ols_other_source_family_bypasses_exact_helper(
    other: str | type, dtype: str, side: str
) -> None:
    strategy = pd.Series([1, 2, 3], dtype=other if side == "strategy" else dtype)
    benchmark = pd.Series([1, 2, 3], dtype=other if side == "benchmark" else dtype)
    expected = BenchmarkComparator().compare(strategy, benchmark)
    if other in {"int64", "Int64", "uint64", "UInt64", "float16", "float32", "Float32"}:
        # ADR-284/285 intentionally admit these original mixed numeric/Float64 pairs.
        with patch.object(
            comparator, "_exact_float64_ols", wraps=comparator._exact_float64_ols
        ) as exact_ols:
            actual = BenchmarkComparator().compare(strategy, benchmark)
        assert exact_ols.call_count == 1
        assert actual.beta == 1
        assert actual.alpha == 0
    else:
        with patch.object(
            comparator,
            "_exact_float64_ols",
            create=True,
            side_effect=AssertionError("outside family"),
        ):
            actual = BenchmarkComparator().compare(strategy, benchmark)
    assert (
        actual.beta,
        actual.alpha,
        actual.information_ratio,
        actual.tracking_error,
        actual.benchmark_relative_drawdown,
    ) == (
        expected.beta,
        expected.alpha,
        expected.information_ratio,
        expected.tracking_error,
        expected.benchmark_relative_drawdown,
    )
    pd.testing.assert_series_equal(actual.excess_returns, expected.excess_returns)


@pytest.mark.parametrize("strategy_dtype", _DTYPES)
@pytest.mark.parametrize("benchmark_dtype", _DTYPES)
def test_float64_ols_full_width_intercept_overflow_refuses(
    strategy_dtype: str, benchmark_dtype: str
) -> None:
    strategy = pd.Series([np.finfo(float).max, math.ulp(0.0), 0], dtype=strategy_dtype)
    benchmark = pd.Series([0, math.ulp(0.0), np.finfo(float).max], dtype=benchmark_dtype)
    with pytest.raises(OverflowError):
        _oracle(strategy, benchmark)
    with pytest.raises(ValueError, match=r"coefficients.*finite"):
        comparator._exact_float64_ols(strategy, benchmark, constant_source=False)
