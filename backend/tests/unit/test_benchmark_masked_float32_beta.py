"""Masked Float32 benchmark variance matches covariance precision (ADR-277)."""

from fractions import Fraction
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from app.research.benchmarks.comparator import BenchmarkComparator

_PARTNERS = [
    "float16",
    "float32",
    "Float32",
    "float64",
    "Float64",
    "int8",
    "int16",
    "int32",
    "int64",
    "Int8",
    "Int16",
    "Int32",
    "Int64",
    "uint8",
    "uint16",
    "uint32",
    "uint64",
    "UInt8",
    "UInt16",
    "UInt32",
    "UInt64",
]


def _oracle(strategy: pd.Series, benchmark: pd.Series) -> float:
    xs = [
        Fraction(int(x)) if isinstance(x, (int, np.integer)) else Fraction(*x.as_integer_ratio())
        for x in strategy
    ]
    ys = [Fraction(*y.as_integer_ratio()) for y in benchmark]
    xm, ym = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((y - ym) ** 2 for y in ys)
    return float(sum((x - xm) * (y - ym) for x, y in zip(xs, ys, strict=True)) / den)


@pytest.mark.parametrize("origin", ["0.1", "0.5", "1", "-0.1"])
@pytest.mark.parametrize("n", [3, 4, 7, 16, 128])
@pytest.mark.parametrize("partner", _PARTNERS)
def test_masked_float32_benchmark_beta_matches_original_fraction_samples(
    origin: str, n: int, partner: str
) -> None:
    base = np.float32(origin)
    values = base + np.arange(n, dtype=np.float32) * np.spacing(base)
    benchmark = pd.Series(values, dtype="Float32", name="return")
    if "int" in partner.lower():
        strategy_values = np.arange(n) % 100
    elif partner == "float16":
        strategy_values = np.arange(n) / 128 + 0.125
    else:
        strategy_values = values.astype(np.float64) * 2 + 0.125
    strategy = pd.Series(strategy_values, dtype=partner, name="return")
    before_strategy, before_benchmark = strategy.copy(deep=True), benchmark.copy(deep=True)
    assert not strategy.eq(strategy.iloc[0]).all()
    with np.errstate(all="raise"):
        state = np.geterr()
        result = BenchmarkComparator().compare(strategy, benchmark)
        assert np.geterr() == state
    assert result.beta == pytest.approx(_oracle(strategy, benchmark), rel=1e-12, abs=0)
    pd.testing.assert_series_equal(strategy, before_strategy)
    pd.testing.assert_series_equal(benchmark, before_benchmark)


@pytest.mark.parametrize("origin", ["0.1", "0.5", "1", "-0.1"])
@pytest.mark.parametrize("n", [3, 4, 7, 16])
def test_masked_float32_same_series_keeps_beta_one_and_alpha_zero(origin: str, n: int) -> None:
    base = np.float32(origin)
    returns = pd.Series(base + np.arange(n, dtype=np.float32) * np.spacing(base), dtype="Float32")
    result = BenchmarkComparator().compare(returns, returns)
    assert result.beta == pytest.approx(1, rel=1e-12, abs=0)
    assert result.alpha == result.information_ratio == result.tracking_error == 0
    assert result.benchmark_relative_drawdown == 0


@pytest.mark.parametrize("scale", [1e-155, 1e-200, 1e-300])
def test_masked_float32_scaled_beta_uses_matched_float64_moments(scale: float) -> None:
    base = np.float32("0.1")
    benchmark = pd.Series(base + np.arange(3, dtype=np.float32) * np.spacing(base), dtype="Float32")
    strategy = pd.Series([scale, 2 * scale, 3 * scale])
    with np.errstate(all="ignore"):
        state = np.geterr()
        result = BenchmarkComparator().compare(strategy, benchmark)
        assert np.geterr() == state
    assert result.beta > 0
    assert result.beta == pytest.approx(_oracle(strategy, benchmark), rel=1e-12, abs=0)


def test_masked_float32_subnormal_benchmark_recovery_matches_fraction_beta() -> None:
    benchmark = pd.Series(np.arange(1, 4, dtype=np.float32) * np.float32("1e-40"), dtype="Float32")
    strategy = pd.Series([1e-300, 2e-300, 3e-300])
    with np.errstate(all="ignore"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta > 0
    assert result.beta == pytest.approx(_oracle(strategy, benchmark), rel=1e-12, abs=0)


@pytest.mark.parametrize("constant_side", ["strategy", "benchmark"])
def test_masked_float32_constant_source_still_bypasses_beta_moments(constant_side: str) -> None:
    strategy = pd.Series([0.01, 0.02, 0.03], dtype="Float32")
    benchmark = pd.Series([0.1, 0.2, 0.3], dtype="Float32")
    if constant_side == "strategy":
        strategy[:] = np.float32("0.1")
    else:
        benchmark[:] = np.float32("0.1")
    with patch.object(pd.Series, "var", side_effect=AssertionError("unused variance")):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == 0


@pytest.mark.parametrize("missing_side", ["strategy", "benchmark"])
def test_masked_float32_aligned_missing_still_refuses(missing_side: str) -> None:
    strategy = pd.Series([0.01, 0.02, 0.03])
    benchmark = pd.Series([0.1, 0.2, 0.3], dtype="Float32")
    (strategy if missing_side == "strategy" else benchmark).iloc[1] = np.nan
    with pytest.raises(ValueError, match="finite"):
        BenchmarkComparator().compare(strategy, benchmark)


def test_masked_float32_beta_respects_partial_overlap_and_names() -> None:
    base = np.float32("0.1")
    values = base + np.arange(3, dtype=np.float32) * np.spacing(base)
    strategy = pd.Series([np.nan, *values], index=[0, 1, 2, 3], name="r", dtype="Float32")
    benchmark = pd.Series([*values, pd.NA], index=[1, 2, 3, 4], name="r", dtype="Float32")
    result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == pytest.approx(1, rel=1e-12, abs=0)
    pd.testing.assert_series_equal(
        result.excess_returns, pd.Series([0, 0, 0], index=[1, 2, 3], name="r", dtype="Float32")
    )


@settings(max_examples=90, deadline=None)
@example(exponent=-4, n=4, slope=1)
@given(exponent=st.integers(-20, 5), n=st.integers(3, 32), slope=st.sampled_from([-1, 1, 2]))
def test_masked_float32_beta_property_preserves_original_affine_variation(
    exponent: int, n: int, slope: int
) -> None:
    base = np.ldexp(np.float32(1), exponent)
    benchmark_values = base + np.arange(n, dtype=np.float32) * np.spacing(base)
    benchmark = pd.Series(benchmark_values, dtype="Float32")
    strategy = pd.Series(
        np.float64(0.125) + slope * (benchmark_values.astype(np.float64) - np.float64(base))
    )
    assert not strategy.eq(strategy.iloc[0]).all()
    assert not benchmark.eq(benchmark.iloc[0]).all()
    assert float(strategy.min()) > -1
    result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == pytest.approx(_oracle(strategy, benchmark), rel=1e-12, abs=0)
    assert result.beta == pytest.approx(slope, rel=1e-12, abs=0)
