"""Classic masked numeric sources and native wider returns retain exact excess evidence."""

from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.benchmarks.comparator import BenchmarkComparator

_MASKED = [
    "Float32",
    "Float64",
    "Int8",
    "Int16",
    "Int32",
    "Int64",
    "UInt8",
    "UInt16",
    "UInt32",
    "UInt64",
]
_WIDE = np.dtype(np.longdouble).itemsize > np.dtype(float).itemsize


def _fraction(value: object) -> Fraction:
    if isinstance(value, (int, np.integer)):
        return Fraction(int(value))
    assert isinstance(value, (float, np.floating))
    return Fraction(*value.as_integer_ratio())


def _oracle(strategy: pd.Series, benchmark: pd.Series) -> float:
    xs, ys = [_fraction(x) for x in benchmark], [_fraction(y) for y in strategy]
    xm, ym = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((x - xm) ** 2 for x in xs)
    if den == 0:
        return 0.0
    return float(sum((x - xm) * (y - ym) for x, y in zip(xs, ys, strict=True)) / den)


def _sources(dtype: str, wide_side: str, n: int = 3) -> tuple[pd.Series, pd.Series]:
    index = pd.date_range("2026-01-01", periods=n, tz="UTC")
    origin = np.longdouble(1)
    step = np.spacing(origin) if _WIDE else np.longdouble("0.125")
    wide = pd.Series([origin + i * step for i in range(n)], index=index, dtype=np.longdouble)
    multiplier = 0.25 if dtype.startswith("Float") else 1
    masked = pd.Series([(i % 3) * multiplier for i in range(n)], index=index, dtype=dtype)
    return (wide, masked) if wide_side == "strategy" else (masked, wide)


def _check(strategy: pd.Series, benchmark: pd.Series) -> None:
    original_strategy, original_benchmark = strategy.copy(deep=True), benchmark.copy(deep=True)
    aligned_strategy, aligned_benchmark = strategy.align(benchmark, join="inner")
    expected = pd.Series(
        aligned_strategy.to_numpy(dtype=np.longdouble)
        - aligned_benchmark.to_numpy(dtype=np.longdouble),
        index=aligned_strategy.index,
        name=(
            pd.Series(dtype=float, name=strategy.name) - pd.Series(dtype=float, name=benchmark.name)
        ).name,
    )
    with np.errstate(all="raise"):
        state = np.geterr()
        result = BenchmarkComparator().compare(strategy, benchmark)
        assert np.geterr() == state
    actual_values = result.excess_returns.to_numpy(dtype=np.longdouble)
    for x, y, actual in zip(aligned_strategy, aligned_benchmark, actual_values, strict=True):
        assert _fraction(actual) == _fraction(x) - _fraction(y)
    if _WIDE:
        pd.testing.assert_series_equal(result.excess_returns, expected, check_exact=True)
    else:
        pd.testing.assert_index_equal(result.excess_returns.index, expected.index)
        np.testing.assert_array_equal(actual_values, expected.to_numpy())
    assert result.beta == pytest.approx(
        _oracle(aligned_strategy, aligned_benchmark), rel=1e-12, abs=0
    )
    pd.testing.assert_series_equal(strategy, original_strategy)
    pd.testing.assert_series_equal(benchmark, original_benchmark)


@pytest.mark.parametrize("dtype", _MASKED)
@pytest.mark.parametrize("wide_side", ["strategy", "benchmark"])
def test_native_wide_masked_pairs_publish_exact_excess_and_beta(dtype: str, wide_side: str) -> None:
    _check(*_sources(dtype, wide_side))


@pytest.mark.parametrize(
    "names",
    [
        (None, None),
        ("same", "same"),
        ("left", "right"),
        (np.nan, np.nan),
        (pd.NA, pd.NA),
        (7, 7),
        (("a", 1), ("a", 1)),
    ],
)
@pytest.mark.parametrize("wide_side", ["strategy", "benchmark"])
def test_native_wide_masked_excess_keeps_pandas_consensus_name(
    names: tuple[object, object], wide_side: str
) -> None:
    strategy, benchmark = _sources("Float64", wide_side)
    strategy.name, benchmark.name = names
    _check(strategy, benchmark)


@pytest.mark.parametrize("dtype", ["Float64", "Int64"])
@pytest.mark.parametrize("wide_side", ["strategy", "benchmark"])
def test_native_wide_masked_excess_keeps_partial_overlap_and_unaligned_missing(
    dtype: str, wide_side: str
) -> None:
    strategy, benchmark = _sources(dtype, wide_side, 5)
    strategy, benchmark = strategy.iloc[:4].copy(), benchmark.iloc[1:].copy()
    masked = benchmark if wide_side == "strategy" else strategy
    masked.iloc[-1 if wide_side == "strategy" else 0] = pd.NA
    _check(strategy, benchmark)


@pytest.mark.parametrize("dtype", ["Float64", "Int64"])
@pytest.mark.parametrize("wide_side", ["strategy", "benchmark"])
def test_native_wide_masked_aligned_missing_refuses_before_excess(
    dtype: str, wide_side: str
) -> None:
    strategy, benchmark = _sources(dtype, wide_side)
    masked = benchmark if wide_side == "strategy" else strategy
    masked.iloc[1] = pd.NA
    with pytest.raises(ValueError, match="finite"):
        BenchmarkComparator().compare(strategy, benchmark)


@pytest.mark.parametrize("wide_side", ["strategy", "benchmark"])
def test_native_wide_masked_constants_keep_beta_zero(wide_side: str) -> None:
    strategy, benchmark = _sources("Float64", wide_side)
    masked = benchmark if wide_side == "strategy" else strategy
    masked.iloc[:] = 0.25
    result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == 0
    assert result.alpha == float(strategy.mean() * 252)


@settings(max_examples=60, deadline=None)
@given(
    dtype=st.sampled_from(_MASKED),
    wide_side=st.sampled_from(["strategy", "benchmark"]),
    n=st.integers(min_value=3, max_value=12),
)
def test_native_wide_masked_dyadic_excess_and_covariance_match_exact_sources(
    dtype: str, wide_side: str, n: int
) -> None:
    _check(*_sources(dtype, wide_side, n))
