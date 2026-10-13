"""Integer OLS intercept is computed before rounding means/beta (ADR-276)."""

from fractions import Fraction
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from hypothesis import example, given, settings
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
_BASE_LIMIT = 2 ** min(60, np.finfo(np.longdouble).nmant - 2) - 100


def _oracle(strategy: pd.Series, benchmark: pd.Series) -> tuple[float, float]:
    xs, ys = [Fraction(int(x)) for x in strategy], [Fraction(int(y)) for y in benchmark]
    xm, ym = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((y - ym) ** 2 for y in ys)
    beta = (
        sum((x - xm) * (y - ym) for x, y in zip(xs, ys, strict=True)) / den if den else Fraction(0)
    )
    return float(beta), float(252 * (xm - beta * ym))


@pytest.mark.parametrize("left", _INTEGER)
@pytest.mark.parametrize("right", _INTEGER)
@pytest.mark.parametrize(
    "a,b", [([0, 3, 2], [1, 2, 4]), ([2, 3, 4], [0, 3, 6]), ([1, 5, 3], [2, 1, 4])]
)
def test_integer_alpha_matches_exact_ols_intercept(
    left: str, right: str, a: list[int], b: list[int]
) -> None:
    strategy, benchmark = pd.Series(a, dtype=left), pd.Series(b, dtype=right)
    before_strategy, before_benchmark = strategy.copy(deep=True), benchmark.copy(deep=True)
    with np.errstate(all="raise"):
        state = np.geterr()
        result = BenchmarkComparator().compare(strategy, benchmark)
        assert np.geterr() == state
    beta, alpha = _oracle(strategy, benchmark)
    assert result.beta == beta
    assert result.alpha == alpha
    pd.testing.assert_series_equal(strategy, before_strategy)
    pd.testing.assert_series_equal(benchmark, before_benchmark)


@pytest.mark.parametrize("left", _LARGE)
@pytest.mark.parametrize("right", _LARGE)
@pytest.mark.parametrize("divisor", [1, 3])
def test_large_integer_alpha_retains_intercept_before_beta_rounding(
    left: str, right: str, divisor: int
) -> None:
    base = _BASE_LIMIT + 100
    strategy = pd.Series([base + i + 2 for i in range(3)], dtype=left)
    benchmark = pd.Series([divisor * (base + i) for i in range(3)], dtype=right)
    result = BenchmarkComparator().compare(strategy, benchmark)
    assert _oracle(strategy, benchmark) == (1 / divisor, 504)
    assert result.beta == 1 / divisor
    assert result.alpha == 504


def test_integer_alpha_full_width_intercept_avoids_published_beta_rounding() -> None:
    base = 2**60
    strategy = pd.Series([base + i + 2 for i in range(3)], dtype="uint64")
    benchmark = pd.Series([3 * (base + i) for i in range(3)], dtype="int64")
    assert _oracle(strategy, benchmark) == (1 / 3, 504)
    assert comparator._exact_integer_alpha(strategy, benchmark, constant_source=False) == 504


@pytest.mark.parametrize("dtype", _INTEGER)
@pytest.mark.parametrize("constant_side", ["strategy", "benchmark"])
def test_integer_alpha_constant_convention_uses_only_exact_mean(
    dtype: str, constant_side: str
) -> None:
    strategy = pd.Series([0, 0, 0, 0, 1], dtype=dtype)
    benchmark = pd.Series([1, 2, 3, 4, 5], dtype=dtype)
    if constant_side == "strategy":
        strategy[:] = 1
    else:
        benchmark[:] = 1
    with (
        patch(
            "app.research.benchmarks.comparator._integer_covariance_sums",
            create=True,
            side_effect=AssertionError("unused covariance sums"),
        ),
        patch(
            "app.research.benchmarks.comparator._exact_integer_beta",
            side_effect=AssertionError("unused beta moments"),
        ),
    ):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == 0
    assert result.alpha == _oracle(strategy, benchmark)[1]
    if constant_side == "benchmark":
        assert result.alpha == float(Fraction(252, 5))


@pytest.mark.parametrize("reverse", [False, True])
def test_integer_alpha_uses_original_aligned_sources(reverse: bool) -> None:
    base = _BASE_LIMIT
    strategy = pd.Series([pd.NA, base + 2, base + 3, base + 4], index=[0, 1, 2, 3], dtype="Int64")
    benchmark = pd.Series(
        [3 * base, 3 * (base + 1), 3 * (base + 2), pd.NA], index=[1, 2, 3, 4], dtype="UInt64"
    )
    if reverse:
        strategy, benchmark = benchmark, strategy
    result = BenchmarkComparator().compare(strategy, benchmark)
    aligned_s, aligned_b = strategy.align(benchmark, join="inner")
    assert result.alpha == _oracle(aligned_s, aligned_b)[1] == (-1512 if reverse else 504)
    assert list(result.excess_returns.index) == [1, 2, 3]


@pytest.mark.parametrize("invalid", [-1, -2, pd.NA])
@pytest.mark.parametrize("reverse", [False, True])
def test_integer_alpha_source_validation_precedes_mean_or_covariance(
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
            "app.research.benchmarks.comparator._exact_integer_alpha",
            create=True,
            side_effect=AssertionError("validate originals first"),
        ),
        pytest.raises(ValueError, match="finite" if invalid is pd.NA else "positive wealth"),
    ):
        BenchmarkComparator().compare(strategy, benchmark)


@settings(max_examples=90, deadline=None)
@example(base=_BASE_LIMIT, n=3, intercept=2, divisor=3, left="uint64", right="Int64")
@given(
    base=st.integers(0, _BASE_LIMIT),
    n=st.integers(3, 12),
    intercept=st.integers(-3, 7),
    divisor=st.sampled_from([1, 3]),
    left=st.sampled_from(_LARGE),
    right=st.sampled_from(_LARGE),
)
def test_integer_alpha_affine_property_retains_exact_intercept(
    base: int, n: int, intercept: int, divisor: int, left: str, right: str
) -> None:
    origin = base + 20
    strategy = pd.Series([origin + i + intercept for i in range(n)], dtype=left)
    benchmark = pd.Series([divisor * (origin + i) for i in range(n)], dtype=right)
    assert int(strategy.min()) >= 0
    assert int(benchmark.max()) <= int(np.iinfo(np.int64).max)
    assert not strategy.eq(strategy.iloc[0]).all()
    assert not benchmark.eq(benchmark.iloc[0]).all()
    result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == _oracle(strategy, benchmark)[0] == 1 / divisor
    assert result.alpha == _oracle(strategy, benchmark)[1] == 252 * intercept
