"""Exact represented narrow-source OLS intercepts (ADR-280)."""

from fractions import Fraction
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from app.research.benchmarks import comparator
from app.research.benchmarks.comparator import BenchmarkComparator

_NARROW = ["float16", "float32", "Float32"]


def _oracle(strategy: pd.Series, benchmark: pd.Series) -> float:
    a = [Fraction(*value.as_integer_ratio()) for value in strategy]
    b = [Fraction(*value.as_integer_ratio()) for value in benchmark]
    mean_a, mean_b = sum(a) / len(a), sum(b) / len(b)
    if len(set(a)) == 1 or len(set(b)) == 1:
        return float(252 * mean_a)
    beta = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b, strict=True)) / sum(
        (y - mean_b) ** 2 for y in b
    )
    return float(252 * (mean_a - beta * mean_b))


@pytest.mark.parametrize("strategy_dtype", _NARROW)
@pytest.mark.parametrize("benchmark_dtype", _NARROW)
@pytest.mark.parametrize("n", [3, 4, 7, 16])
@pytest.mark.parametrize("origin", [0.1, 0.5, 1.0])
@pytest.mark.parametrize("slope", [1, 2])
def test_narrow_alpha_matches_exact_original_ols_intercept(
    strategy_dtype: str, benchmark_dtype: str, n: int, origin: float, slope: int
) -> None:
    # A common float16 lattice ensures every mixed-width source retains exact affine values.
    base = np.float16(origin)
    values = base + np.arange(n, dtype=np.float16) * np.spacing(base)
    benchmark = pd.Series(values, dtype=benchmark_dtype, name="r")
    strategy = pd.Series(slope * values + slope * np.spacing(base), dtype=strategy_dtype, name="r")
    expected = _oracle(strategy, benchmark)
    assert expected > 0
    before_s, before_b = strategy.copy(deep=True), benchmark.copy(deep=True)
    with np.errstate(all="raise"):
        state = np.geterr()
        result = BenchmarkComparator().compare(strategy, benchmark)
        assert np.geterr() == state
    assert result.alpha == expected
    pd.testing.assert_series_equal(result.excess_returns, strategy - benchmark)
    pd.testing.assert_series_equal(strategy, before_s)
    pd.testing.assert_series_equal(benchmark, before_b)


@pytest.mark.parametrize("dtype,n", [("float16", 4), ("float32", 3), ("Float32", 3)])
def test_narrow_alpha_does_not_erase_one_original_ulp_offset(dtype: str, n: int) -> None:
    native = np.float16 if dtype == "float16" else np.float32
    base = native(0.1)
    benchmark = pd.Series(base + np.arange(n, dtype=native) * np.spacing(base), dtype=dtype)
    strategy = benchmark + np.spacing(base)
    expected = _oracle(strategy, benchmark)
    assert expected == float(252 * Fraction(*np.spacing(base).as_integer_ratio()))
    result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.alpha == expected
    assert result.alpha > 0


@pytest.mark.parametrize("strategy_dtype", _NARROW)
@pytest.mark.parametrize("benchmark_dtype", _NARROW)
@pytest.mark.parametrize("constant_side", ["strategy", "benchmark", "both"])
@pytest.mark.parametrize("value", [0.1, -0.1, 0.125])
def test_narrow_alpha_constant_source_keeps_exact_mean_only_convention(
    strategy_dtype: str, benchmark_dtype: str, constant_side: str, value: float
) -> None:
    strategy = pd.Series(
        [value] * 3 if constant_side != "benchmark" else [0.1, 0.2, 0.3],
        dtype=strategy_dtype,
    )
    benchmark = pd.Series(
        [value] * 3 if constant_side != "strategy" else [0.1, 0.2, 0.3],
        dtype=benchmark_dtype,
    )
    with patch.object(pd.Series, "cov", side_effect=AssertionError("unused covariance")):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == 0
    assert result.alpha == _oracle(strategy, benchmark)


@pytest.mark.parametrize("strategy_dtype", _NARROW)
@pytest.mark.parametrize("benchmark_dtype", _NARROW)
@pytest.mark.parametrize("constant_side", ["strategy", "benchmark", "neither"])
def test_narrow_alpha_full_source_width_direct_helper_matches_fraction(
    strategy_dtype: str, benchmark_dtype: str, constant_side: str
) -> None:
    ns = np.float16 if strategy_dtype == "float16" else np.float32
    nb = np.float16 if benchmark_dtype == "float16" else np.float32
    strategy = pd.Series(
        [np.finfo(ns).max, np.finfo(ns).smallest_subnormal, 0], dtype=strategy_dtype
    )
    benchmark = pd.Series(
        [0, np.finfo(nb).smallest_subnormal, np.finfo(nb).max], dtype=benchmark_dtype
    )
    if constant_side == "strategy":
        strategy[:] = strategy.iloc[0]
    elif constant_side == "benchmark":
        benchmark[:] = benchmark.iloc[1]
    with np.errstate(all="raise"):
        state = np.geterr()
        actual = comparator._exact_narrow_alpha(
            strategy, benchmark, constant_source=constant_side != "neither"
        )
        assert np.geterr() == state
    assert actual == _oracle(strategy, benchmark)
    assert np.isfinite(actual)


@pytest.mark.parametrize("dtype", _NARROW)
def test_narrow_alpha_preserves_alignment_metadata_and_source_refusals(
    dtype: str,
) -> None:
    strategy = pd.Series([np.nan, 0.1, 0.2, 0.3], index=[0, 1, 2, 3], dtype=dtype, name="a")
    benchmark = pd.Series([0.2, 0.3, 0.4, np.nan], index=[1, 2, 3, 4], dtype=dtype, name="b")
    s, b = strategy.align(benchmark, join="inner")
    result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.alpha == _oracle(s, b)
    pd.testing.assert_series_equal(result.excess_returns, s - b)
    for invalid in [np.nan, np.inf, -1.0]:
        bad = strategy.copy()
        bad.iloc[2] = invalid
        with pytest.raises(ValueError, match=r"finite|wealth"):
            BenchmarkComparator().compare(bad, benchmark)
    with pytest.raises(ValueError, match="at least two"):
        BenchmarkComparator().compare(s.iloc[:1], b.iloc[:1])


@settings(max_examples=90, deadline=None)
@example(
    strategy_dtype="float32",
    benchmark_dtype="Float32",
    exponent=-12,
    n=3,
    slope=1,
    offset=-1,
)
@given(
    strategy_dtype=st.sampled_from(_NARROW),
    benchmark_dtype=st.sampled_from(_NARROW),
    exponent=st.integers(-12, 4),
    n=st.integers(3, 16),
    slope=st.integers(1, 3),
    offset=st.integers(-3, 3),
)
def test_narrow_alpha_property_uses_exact_unrounded_fit(
    strategy_dtype: str,
    benchmark_dtype: str,
    exponent: int,
    n: int,
    slope: int,
    offset: int,
) -> None:
    base = np.ldexp(np.float16(1), exponent)
    step = np.spacing(base)
    values = base + np.arange(n, dtype=np.float16) * step
    strategy = pd.Series(slope * values + offset * step, dtype=strategy_dtype)
    benchmark = pd.Series(values, dtype=benchmark_dtype)
    assert not strategy.eq(strategy.iloc[0]).all()
    assert not benchmark.eq(benchmark.iloc[0]).all()
    expected = _oracle(strategy, benchmark)
    with np.errstate(all="raise"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.alpha == expected


@pytest.mark.parametrize("narrow", _NARROW)
@pytest.mark.parametrize("other", ["float64", "Float64", "int32", "UInt32", "longdouble"])
@pytest.mark.parametrize("reverse", [False, True])
def test_narrow_alpha_does_not_change_mixed_other_source_families(
    narrow: str, other: str, reverse: bool
) -> None:
    a = pd.Series([0.1, 0.2, 0.3], dtype=narrow)
    b = pd.Series([0, 1, 2], dtype=other)
    if reverse:
        a, b = b, a
    with patch(
        "app.research.benchmarks.comparator._exact_narrow_alpha",
        create=True,
        side_effect=AssertionError("unused narrow alpha"),
    ):
        result = BenchmarkComparator().compare(a, b)
    assert np.isfinite(result.alpha)
    pd.testing.assert_series_equal(result.excess_returns.index.to_series(), a.index.to_series())
