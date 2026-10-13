"""Native-wide beta uses matched moments of original represented observations."""

from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.benchmarks.comparator import BenchmarkComparator

_WIDE = np.finfo(np.longdouble).nmant > np.finfo(float).nmant
_EXTENDED_RANGE = np.finfo(np.longdouble).minexp < np.finfo(float).minexp


def _fraction(value: object) -> Fraction:
    if isinstance(value, (int, np.integer)):
        return Fraction(int(value))
    assert isinstance(value, (float, np.floating))
    return Fraction(*value.as_integer_ratio())


def _oracle(strategy: pd.Series, benchmark: pd.Series) -> float:
    xs, ys = [_fraction(x) for x in benchmark], [_fraction(y) for y in strategy]
    xm, ym = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((x - xm) ** 2 for x in xs)
    return float(sum((x - xm) * (y - ym) for x, y in zip(xs, ys, strict=True)) / den)


def _neighbors(base: str | np.longdouble, n: int = 3) -> pd.Series:
    origin = np.longdouble(base)
    step = np.spacing(origin) if _WIDE else origin / 8
    return pd.Series([origin + i * step for i in range(n)], dtype=np.longdouble)


@pytest.mark.parametrize("base", ["1", "0.1", "0.5"])
@pytest.mark.parametrize("strict", [False, True])
def test_beta_native_wide_same_series_is_one(base: str, strict: bool) -> None:
    returns = _neighbors(base)
    assert not returns.eq(returns.iloc[0]).all()
    if _WIDE:
        assert np.all(returns.to_numpy(dtype=float) == float(returns.iloc[0]))
    with np.errstate(all="raise" if strict else "ignore"):
        state = np.geterr()
        result = BenchmarkComparator().compare(returns, returns)
        assert np.geterr() == state
    assert _oracle(returns, returns) == 1
    assert result.beta == 1
    assert result.alpha == 0
    assert (
        result.information_ratio == result.tracking_error == result.benchmark_relative_drawdown == 0
    )


@pytest.mark.parametrize("base", ["1", "0.1", "0.5"])
@pytest.mark.parametrize("slope", [-0.5, 0.5, 1.0, 2.0])
def test_beta_native_wide_affine_sources_match_exact_represented_oracle(
    base: str, slope: float
) -> None:
    benchmark = _neighbors(base)
    strategy = slope * benchmark + np.longdouble("0.125")
    before_strategy, before_benchmark = strategy.copy(deep=True), benchmark.copy(deep=True)
    with np.errstate(all="ignore"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == pytest.approx(_oracle(strategy, benchmark), rel=1e-12, abs=0)
    assert result.alpha == float((strategy.mean() - result.beta * benchmark.mean()) * 252)
    pd.testing.assert_series_equal(strategy, before_strategy)
    pd.testing.assert_series_equal(benchmark, before_benchmark)
    pd.testing.assert_series_equal(result.excess_returns, strategy - benchmark)


@pytest.mark.parametrize("wide_side", ["strategy", "benchmark"])
@pytest.mark.parametrize("partner_dtype", ["float64", "float32", "int64"])
def test_beta_native_wide_and_ordinary_partners_use_matched_original_values(
    wide_side: str, partner_dtype: str
) -> None:
    wide = _neighbors("1")
    values = [1, 2, 3] if partner_dtype == "int64" else [0.01, 0.02, 0.03]
    partner = pd.Series(values, dtype=partner_dtype)
    strategy = wide if wide_side == "strategy" else partner
    benchmark = wide if wide_side == "benchmark" else partner
    with np.errstate(all="ignore"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == pytest.approx(_oracle(strategy, benchmark), rel=1e-12, abs=0)


def test_beta_native_wide_denominator_is_not_narrowed_before_quotient() -> None:
    scale = np.longdouble("1e-2400") if _EXTENDED_RANGE else np.longdouble("0.125")
    returns = pd.Series([0, scale, 2 * scale], dtype=np.longdouble)
    if _EXTENDED_RANGE:
        assert float(scale * scale) == 0
    with np.errstate(all="ignore"):
        result = BenchmarkComparator().compare(returns, returns)
    assert result.beta == 1


def test_beta_native_wide_does_not_compute_unused_strategy_variance() -> None:
    scale = np.longdouble("1e-2500") if _EXTENDED_RANGE else np.longdouble("0.125")
    benchmark = pd.Series([1, 2, 3], dtype=np.longdouble)
    strategy = scale * benchmark
    with np.errstate(all="ignore"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == _oracle(strategy, benchmark)


def test_beta_unmeasurable_needed_native_wide_moments_refuse() -> None:
    if _WIDE:
        scale = np.ldexp(np.longdouble(1), np.finfo(np.longdouble).minexp // 2 - 100)
        returns = pd.Series([scale, 2 * scale, 3 * scale], dtype=np.longdouble)
        assert scale > 0 and _oracle(returns, returns) == 1
        with np.errstate(all="ignore"), pytest.raises(ValueError, match=r"native.wide.*measurable"):
            BenchmarkComparator().compare(returns, returns)
    else:
        # Platforms without native extra precision retain the ordinary estimator.
        returns = _neighbors("1")
        assert BenchmarkComparator().compare(returns, returns).beta == 1


def test_beta_native_wide_keeps_partial_overlap_identity() -> None:
    full = _neighbors("1", 5)
    strategy = full.iloc[:4].copy()
    benchmark = full.iloc[1:].copy()
    with np.errstate(all="ignore"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == 1
    assert list(result.excess_returns.index) == [1, 2, 3]
    assert result.excess_returns.eq(0).all()


@settings(max_examples=70, deadline=None)
@given(
    exponent=st.integers(min_value=-30, max_value=0),
    n=st.integers(min_value=3, max_value=12),
    slope=st.sampled_from([-0.5, 0.5, 1.0, 2.0]),
)
def test_beta_native_wide_dyadic_affine_samples_match_exact_source_ratio(
    exponent: int, n: int, slope: float
) -> None:
    benchmark = _neighbors(np.ldexp(np.longdouble(1), exponent), n)
    values = benchmark.to_numpy(dtype=np.longdouble)
    strategy = pd.Series(
        np.longdouble(slope) * (values - values[0]) + values[0],
        index=benchmark.index,
        dtype=np.longdouble,
    )
    assert not benchmark.eq(benchmark.iloc[0]).all()
    assert not strategy.eq(strategy.iloc[0]).all()
    with np.errstate(all="ignore"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == pytest.approx(_oracle(strategy, benchmark), rel=1e-12, abs=0)
