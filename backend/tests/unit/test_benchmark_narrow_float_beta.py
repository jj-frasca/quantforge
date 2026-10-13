"""Native float16/32 benchmark variance matches float64 covariance (ADR-278)."""

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
    def exact(value: object) -> Fraction:
        if isinstance(value, (int, np.integer)):
            return Fraction(int(value))
        assert isinstance(value, (float, np.floating))
        return Fraction(*value.as_integer_ratio())

    xs, ys = [exact(x) for x in strategy], [exact(y) for y in benchmark]
    xm, ym = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((y - ym) ** 2 for y in ys)
    return float(sum((x - xm) * (y - ym) for x, y in zip(xs, ys, strict=True)) / den)


@pytest.mark.parametrize("benchmark_dtype", ["float16", "float32"])
@pytest.mark.parametrize("origin", ["0.1", "0.5", "1", "-0.1"])
@pytest.mark.parametrize("n", [3, 4, 7, 16, 128])
@pytest.mark.parametrize("partner", _PARTNERS)
def test_native_narrow_benchmark_beta_matches_original_fraction_samples(
    benchmark_dtype: str, origin: str, n: int, partner: str
) -> None:
    native = np.float16 if benchmark_dtype == "float16" else np.float32
    base = native(origin)
    values = base + np.arange(n, dtype=native) * np.spacing(base)
    benchmark = pd.Series(values, dtype=benchmark_dtype, name="r")
    if "int" in partner.lower():
        strategy_values = np.arange(n) % 100
    elif partner == "float16":
        strategy_values = values if benchmark_dtype == "float16" else np.arange(n) / 128 + 0.125
    else:
        strategy_values = values.astype(np.float64) * 2 + 0.125
    strategy = pd.Series(strategy_values, dtype=partner, name="r")
    # Installed pandas cannot subtract these masked/native pairs; preserve that
    # separate, documented compatibility failure instead of claiming it fixed.
    if benchmark_dtype == "float16" and partner in ("Int8", "UInt8"):
        with pytest.raises(TypeError, match=r"FloatingArray does not support np\.float16"):
            BenchmarkComparator().compare(strategy, benchmark)
        return
    assert not strategy.eq(strategy.iloc[0]).all()
    before_strategy, before_benchmark = strategy.copy(deep=True), benchmark.copy(deep=True)
    with np.errstate(all="raise"):
        state = np.geterr()
        result = BenchmarkComparator().compare(strategy, benchmark)
        assert np.geterr() == state
    assert result.beta == pytest.approx(_oracle(strategy, benchmark), rel=1e-12, abs=0)
    pd.testing.assert_series_equal(strategy, before_strategy)
    pd.testing.assert_series_equal(benchmark, before_benchmark)


@pytest.mark.parametrize(
    "dtype,values",
    [("float16", [0, 0, 444]), ("float16", [1000, 2000, 3000]), ("float32", [1e20, 2e20, 3e20])],
)
def test_narrow_float_same_series_large_variance_keeps_beta_one_alpha_zero(
    dtype: str, values: list[float]
) -> None:
    returns = pd.Series(values, dtype=dtype)
    with np.errstate(all="raise"):
        result = BenchmarkComparator().compare(returns, returns)
    assert result.beta == pytest.approx(1, rel=1e-12, abs=0)
    assert result.alpha == result.information_ratio == result.tracking_error == 0
    assert result.benchmark_relative_drawdown == 0


@pytest.mark.parametrize("dtype", ["float16", "float32"])
@pytest.mark.parametrize("scale", [1e-155, 1e-200, 1e-300])
def test_native_narrow_beta_scaled_recovery_uses_matched_float64(dtype: str, scale: float) -> None:
    native = np.float16 if dtype == "float16" else np.float32
    base = native("0.1")
    benchmark = pd.Series(base + np.arange(3, dtype=native) * np.spacing(base), dtype=dtype)
    strategy = pd.Series([scale, 2 * scale, 3 * scale])
    with np.errstate(all="ignore"):
        state = np.geterr()
        result = BenchmarkComparator().compare(strategy, benchmark)
        assert np.geterr() == state
    assert result.beta > 0
    assert result.beta == pytest.approx(_oracle(strategy, benchmark), rel=1e-12, abs=0)


@pytest.mark.parametrize("dtype", ["float16", "float32"])
@pytest.mark.parametrize("constant_side", ["strategy", "benchmark"])
def test_native_narrow_constant_source_bypasses_beta_moments(
    dtype: str, constant_side: str
) -> None:
    strategy, benchmark = pd.Series([0.01, 0.02, 0.03]), pd.Series([0.1, 0.2, 0.3], dtype=dtype)
    if constant_side == "strategy":
        strategy[:] = 0.125
    else:
        benchmark[:] = 0.125
    with patch.object(pd.Series, "var", side_effect=AssertionError("unused beta variance")):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == 0


@pytest.mark.parametrize("dtype", ["float16", "float32"])
def test_native_narrow_beta_keeps_overlap_and_missing_guards(dtype: str) -> None:
    native = np.float16 if dtype == "float16" else np.float32
    base = native("0.1")
    values = base + np.arange(3, dtype=native) * np.spacing(base)
    strategy = pd.Series([np.nan, *values.astype(np.float64)], index=[0, 1, 2, 3], name="r")
    benchmark = pd.Series([*values, np.nan], index=[1, 2, 3, 4], name="r", dtype=dtype)
    result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == pytest.approx(1, rel=1e-12, abs=0)
    assert list(result.excess_returns.index) == [1, 2, 3]
    assert result.excess_returns.name == "r"
    benchmark.iloc[1] = np.nan
    with pytest.raises(ValueError, match="finite"):
        BenchmarkComparator().compare(strategy, benchmark)


@settings(max_examples=90, deadline=None)
@example(benchmark_dtype="float32", exponent=-60, n=4, slope=1)
@given(
    benchmark_dtype=st.sampled_from(["float16", "float32"]),
    exponent=st.integers(-8, 4),
    n=st.integers(3, 32),
    slope=st.sampled_from([-1, 1, 2]),
)
def test_native_narrow_beta_affine_property_preserves_represented_variation(
    benchmark_dtype: str, exponent: int, n: int, slope: int
) -> None:
    native = np.float16 if benchmark_dtype == "float16" else np.float32
    base = np.ldexp(native(1), exponent)
    values = base + np.arange(n, dtype=native) * np.spacing(base)
    benchmark = pd.Series(values, dtype=benchmark_dtype)
    strategy = pd.Series(2 * np.float64(base) + slope * values.astype(np.float64))
    assert not strategy.eq(strategy.iloc[0]).all()
    assert not benchmark.eq(benchmark.iloc[0]).all()
    assert float(strategy.min()) > -1
    with np.errstate(all="raise"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == pytest.approx(_oracle(strategy, benchmark), rel=1e-12, abs=0)
    assert result.beta == pytest.approx(slope, rel=1e-12, abs=0)
