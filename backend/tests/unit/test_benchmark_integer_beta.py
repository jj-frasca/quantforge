"""Integer beta uses exact centered covariance sufficient sums (ADR-275)."""

from fractions import Fraction
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.benchmarks import comparator
from app.research.benchmarks.comparator import BenchmarkComparator

_INTEGER = [
    "int8",
    "int16",
    "int32",
    "int64",
    "uint8",
    "uint16",
    "uint32",
    "uint64",
    "Int8",
    "Int16",
    "Int32",
    "Int64",
    "UInt8",
    "UInt16",
    "UInt32",
    "UInt64",
]
_LARGE = ["int64", "Int64", "uint64", "UInt64"]


def _oracle(strategy: pd.Series, benchmark: pd.Series) -> float:
    strategy_values = [Fraction(int(value)) for value in strategy]
    benchmark_values = [Fraction(int(value)) for value in benchmark]
    strategy_mean = sum(strategy_values) / len(strategy_values)
    benchmark_mean = sum(benchmark_values) / len(benchmark_values)
    denominator = sum((value - benchmark_mean) ** 2 for value in benchmark_values)
    if denominator == 0:
        return 0.0
    numerator = sum(
        (a - strategy_mean) * (b - benchmark_mean)
        for a, b in zip(strategy_values, benchmark_values, strict=True)
    )
    return float(numerator / denominator)


@pytest.mark.parametrize("left", _INTEGER)
@pytest.mark.parametrize("right", _INTEGER)
@pytest.mark.parametrize(
    "a,b", [([0, 3, 2], [1, 2, 4]), ([3, 2, 1], [1, 2, 3]), ([1, 2, 3], [1, 0, 1])]
)
def test_integer_beta_matches_exact_centered_covariance(
    left: str, right: str, a: list[int], b: list[int]
) -> None:
    strategy, benchmark = pd.Series(a, dtype=left), pd.Series(b, dtype=right)
    before_strategy, before_benchmark = strategy.copy(deep=True), benchmark.copy(deep=True)
    with np.errstate(all="raise"):
        state = np.geterr()
        result = BenchmarkComparator().compare(strategy, benchmark)
        assert np.geterr() == state
    assert result.beta == _oracle(strategy, benchmark)
    assert result.alpha == float((strategy.mean() - result.beta * benchmark.mean()) * 252)
    pd.testing.assert_series_equal(strategy, before_strategy)
    pd.testing.assert_series_equal(benchmark, before_benchmark)


@pytest.mark.parametrize("dtype", _LARGE)
def test_large_integer_same_series_retains_beta_one_and_alpha_zero(dtype: str) -> None:
    base = int(np.iinfo(np.int64).max) - 4
    returns = pd.Series([base, base + 1, base + 2], dtype=dtype)
    assert not returns.eq(returns.iloc[0]).all()
    result = BenchmarkComparator().compare(returns, returns)
    assert result.beta == 1
    assert result.alpha == result.information_ratio == result.tracking_error == 0
    assert result.benchmark_relative_drawdown == 0


@pytest.mark.parametrize("left", _LARGE)
@pytest.mark.parametrize("right", _LARGE)
@pytest.mark.parametrize("slope", [-1, 1, 2])
def test_large_integer_affine_beta_survives_source_moment_narrowing(
    left: str, right: str, slope: int
) -> None:
    base = 2**62
    strategy = pd.Series([base + slope * i for i in range(3)], dtype=left)
    benchmark = pd.Series([base + i for i in range(3)], dtype=right)
    result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == _oracle(strategy, benchmark) == slope


@pytest.mark.parametrize("left", ["uint64", "UInt64"])
@pytest.mark.parametrize("right", _LARGE)
def test_large_integer_zero_covariance_is_exact_not_native_roundoff(left: str, right: str) -> None:
    # Existing exact excess encoding remains authoritative on narrower platforms.
    maximum = 2 ** min(63, np.finfo(np.longdouble).nmant + 1) - 1
    strategy = pd.Series([maximum - 2, 0, 2 * maximum - 1], dtype=left)
    benchmark = pd.Series([0, maximum, maximum - 1], dtype=right)
    assert _oracle(strategy, benchmark) == 0
    result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == 0


def test_integer_beta_full_width_zero_covariance_uses_exact_sums() -> None:
    maximum = int(np.iinfo(np.int64).max)
    strategy = pd.Series([maximum - 2, 0, 2 * maximum - 1], dtype="uint64")
    benchmark = pd.Series([0, maximum, maximum - 1], dtype="int64")
    assert _oracle(strategy, benchmark) == 0
    assert comparator._exact_integer_beta(strategy, benchmark) == 0


@pytest.mark.parametrize("dtype", _INTEGER)
@pytest.mark.parametrize("constant_side", ["strategy", "benchmark"])
def test_integer_beta_exact_constant_precedes_moments(dtype: str, constant_side: str) -> None:
    strategy, benchmark = pd.Series([0, 1, 2], dtype=dtype), pd.Series([1, 2, 3], dtype=dtype)
    if constant_side == "strategy":
        strategy[:] = 1
    else:
        benchmark[:] = 1
    with patch(
        "app.research.benchmarks.comparator._exact_integer_beta",
        create=True,
        side_effect=AssertionError("unused integer moments"),
    ):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == 0


@pytest.mark.parametrize("reverse", [False, True])
def test_integer_beta_uses_original_aligned_observations(reverse: bool) -> None:
    base = 2**62
    strategy = pd.Series([pd.NA, base, base + 2, base + 4], index=[0, 1, 2, 3], dtype="Int64")
    benchmark = pd.Series([base, base + 1, base + 2, pd.NA], index=[1, 2, 3, 4], dtype="UInt64")
    if reverse:
        strategy, benchmark = benchmark, strategy
    result = BenchmarkComparator().compare(strategy, benchmark)
    assert list(result.excess_returns.index) == [1, 2, 3]
    assert result.beta == (0.5 if reverse else 2)


@pytest.mark.parametrize("invalid", [-1, -2, pd.NA])
@pytest.mark.parametrize("reverse", [False, True])
def test_integer_beta_original_source_guards_precede_exact_moments(
    invalid: object, reverse: bool
) -> None:
    strategy, benchmark = (
        pd.Series([0, invalid, 2], dtype="Int64"),
        pd.Series([1, 2, 3], dtype="UInt64"),
    )
    if reverse:
        strategy, benchmark = benchmark, strategy
    with (
        patch(
            "app.research.benchmarks.comparator._exact_integer_beta",
            create=True,
            side_effect=AssertionError("must validate sources first"),
        ),
        pytest.raises(ValueError, match="finite" if invalid is pd.NA else "positive wealth"),
    ):
        BenchmarkComparator().compare(strategy, benchmark)


@settings(max_examples=90, deadline=None)
@given(
    base=st.integers(0, 2**63 - 200),
    n=st.integers(3, 12),
    step=st.integers(1, 3),
    slope=st.sampled_from([-1, 1, 2, 3]),
    left=st.sampled_from(_LARGE),
    right=st.sampled_from(_LARGE),
)
def test_integer_beta_affine_property_preserves_original_differences(
    base: int, n: int, step: int, slope: int, left: str, right: str
) -> None:
    origin = base + 40
    strategy = pd.Series([origin + slope * i * step for i in range(n)], dtype=left)
    benchmark = pd.Series([origin + i * step for i in range(n)], dtype=right)
    assert 0 <= int(strategy.min()) <= int(strategy.max()) <= int(np.iinfo(np.int64).max)
    assert not strategy.eq(strategy.iloc[0]).all()
    assert not benchmark.eq(benchmark.iloc[0]).all()
    result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == _oracle(strategy, benchmark) == slope
