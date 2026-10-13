"""Narrow excess dispersion and stable means retain represented evidence (ADR-279)."""

from decimal import Decimal, localcontext
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


def _oracle(excess: pd.Series) -> tuple[float, float]:
    values = [Fraction(*value.as_integer_ratio()) for value in excess]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    assert variance > 0
    with localcontext() as context:
        context.prec = 160
        std = (Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt()
        root = Decimal.from_float(float(np.sqrt(252)))
        ir = root * Decimal(mean.numerator) / Decimal(mean.denominator) / std
        return float(ir), float(root * std)


@pytest.mark.parametrize("dtype", _NARROW)
@pytest.mark.parametrize("origin", ["0.1", "0.5", "1"])
@pytest.mark.parametrize("n", [3, 4, 7, 16])
@pytest.mark.parametrize("strict", [False, True])
def test_narrow_excess_moments_match_original_fraction_observations(
    dtype: str, origin: str, n: int, strict: bool
) -> None:
    native = np.float16 if dtype == "float16" else np.float32
    base = native(origin)
    strategy = pd.Series(
        base + np.arange(n, dtype=native) * np.spacing(base), dtype=dtype, name="r"
    )
    benchmark = pd.Series([0] * n, dtype=dtype, name="r")
    before_strategy, before_benchmark = strategy.copy(deep=True), benchmark.copy(deep=True)
    expected_ir, expected_te = _oracle(strategy)
    with np.errstate(all="raise" if strict else "ignore"):
        state = np.geterr()
        result = BenchmarkComparator().compare(strategy, benchmark)
        assert np.geterr() == state
    assert result.information_ratio == pytest.approx(expected_ir, rel=1e-12, abs=0)
    assert result.tracking_error == pytest.approx(expected_te, rel=1e-12, abs=0)
    pd.testing.assert_series_equal(result.excess_returns, strategy)
    pd.testing.assert_series_equal(strategy, before_strategy)
    pd.testing.assert_series_equal(benchmark, before_benchmark)


@pytest.mark.parametrize(
    "dtype,scale",
    [
        ("float16", 1e-6),
        ("float32", 1e-24),
        ("Float32", 1e-24),
        ("float32", 1e30),
        ("Float32", 1e30),
    ],
)
def test_narrow_excess_variance_underflow_overflow_does_not_invent_zero_risk(
    dtype: str, scale: float
) -> None:
    strategy = pd.Series([scale, 2 * scale, 3 * scale], dtype=dtype)
    benchmark = pd.Series([0, 0, 0], dtype=dtype)
    with np.errstate(all="ignore"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    expected_ir, expected_te = _oracle(strategy)
    assert result.information_ratio > 0
    assert result.tracking_error > 0
    assert result.information_ratio == pytest.approx(expected_ir, rel=1e-12, abs=0)
    assert result.tracking_error == pytest.approx(expected_te, rel=1e-12, abs=0)


@pytest.mark.parametrize("dtype", _NARROW)
@pytest.mark.parametrize("zero_mean", [False, True])
def test_narrow_excess_cancellation_preserves_true_mean_and_measurable_risk(
    dtype: str, zero_mean: bool
) -> None:
    maximum = 256 if dtype == "float16" else 1e20
    tiny = 0 if zero_mean else (1e-6 if dtype == "float16" else 1e-24)
    strategy = pd.Series([maximum, tiny, 0], dtype=dtype)
    benchmark = pd.Series([0, 0, maximum], dtype=dtype)
    expected_excess = strategy - benchmark
    assert float(expected_excess.sum()) == 0
    if dtype != "float16":
        assert float(expected_excess.astype(np.float64).sum()) == 0
    expected_ir, expected_te = _oracle(expected_excess)
    with np.errstate(all="ignore"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    pd.testing.assert_series_equal(result.excess_returns, expected_excess)
    assert result.tracking_error > 0
    assert result.information_ratio == pytest.approx(expected_ir, rel=1e-12, abs=0)
    assert result.tracking_error == pytest.approx(expected_te, rel=1e-12, abs=0)
    if zero_mean:
        assert result.information_ratio == 0
    else:
        assert result.information_ratio > 0


@pytest.mark.parametrize("dtype", _NARROW)
def test_narrow_excess_full_width_internal_moments_remain_measurable(dtype: str) -> None:
    native = np.float16 if dtype == "float16" else np.float32
    limits = np.finfo(native)
    excess = pd.Series([limits.max, limits.smallest_subnormal, -limits.max], dtype=dtype)
    expected_ir, expected_te = _oracle(excess)
    with np.errstate(all="raise"):
        state = np.geterr()
        mean, std = comparator._narrow_excess_moments(excess)
        assert np.geterr() == state
    assert mean > 0 and std > 0
    assert float(np.sqrt(252) * mean / std) == pytest.approx(expected_ir, rel=1e-12, abs=0)
    assert float(np.sqrt(252) * std) == pytest.approx(expected_te, rel=1e-12, abs=0)


@pytest.mark.parametrize("dtype", _NARROW)
@pytest.mark.parametrize("value", [0.1, -0.1, 0.125])
def test_narrow_exact_constant_excess_bypasses_all_new_moments(dtype: str, value: float) -> None:
    strategy, benchmark = pd.Series([value] * 3, dtype=dtype), pd.Series([0] * 3, dtype=dtype)
    with patch(
        "app.research.benchmarks.comparator._narrow_excess_moments",
        create=True,
        side_effect=AssertionError("unused narrow moments"),
    ):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.information_ratio == result.tracking_error == 0


@pytest.mark.parametrize("dtype", _NARROW)
@pytest.mark.parametrize("names", [("r", "r"), (np.nan, np.nan), (pd.NA, pd.NA), ("a", "b")])
def test_narrow_excess_moments_preserve_overlap_metadata_and_missing_guard(
    dtype: str, names: tuple[object, object]
) -> None:
    strategy = pd.Series([np.nan, 0.1, 0.2, 0.3], index=[0, 1, 2, 3], dtype=dtype, name=names[0])
    benchmark = pd.Series([0, 0, 0, np.nan], index=[1, 2, 3, 4], dtype=dtype, name=names[1])
    aligned_s, aligned_b = strategy.align(benchmark, join="inner")
    expected_excess = aligned_s - aligned_b
    result = BenchmarkComparator().compare(strategy, benchmark)
    pd.testing.assert_series_equal(result.excess_returns, expected_excess)
    expected_ir, expected_te = _oracle(expected_excess)
    assert result.information_ratio == pytest.approx(expected_ir, rel=1e-12, abs=0)
    assert result.tracking_error == pytest.approx(expected_te, rel=1e-12, abs=0)
    strategy.iloc[2] = np.nan
    with pytest.raises(ValueError, match="finite"):
        BenchmarkComparator().compare(strategy, benchmark)


@settings(max_examples=90, deadline=None)
@example(dtype="float16", exponent=-12, n=3)
@example(dtype="Float32", exponent=-12, n=4)
@given(dtype=st.sampled_from(_NARROW), exponent=st.integers(-12, 4), n=st.integers(3, 12))
def test_narrow_excess_property_keeps_original_nonconstant_risk(
    dtype: str, exponent: int, n: int
) -> None:
    native = np.float16 if dtype == "float16" else np.float32
    base = np.ldexp(native(1), exponent)
    strategy = pd.Series(base + np.arange(n, dtype=native) * np.spacing(base), dtype=dtype)
    benchmark = pd.Series([0] * n, dtype=dtype)
    assert not strategy.eq(strategy.iloc[0]).all()
    expected_ir, expected_te = _oracle(strategy)
    with np.errstate(all="raise"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.tracking_error > 0
    assert result.information_ratio == pytest.approx(expected_ir, rel=1e-12, abs=0)
    assert result.tracking_error == pytest.approx(expected_te, rel=1e-12, abs=0)
