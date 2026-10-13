"""Exact represented excess constants and native-wide sample dispersion (ADR-272)."""

from decimal import Decimal, localcontext
from fractions import Fraction
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.benchmarks.comparator import BenchmarkComparator

_WIDE = np.finfo(np.longdouble).nmant > np.finfo(float).nmant
_EXTENDED_RANGE = np.finfo(np.longdouble).minexp < np.finfo(float).minexp


def _oracle(excess: pd.Series) -> tuple[float, float]:
    values = [Fraction(*x.as_integer_ratio()) for x in excess]
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    assert variance > 0
    with localcontext() as context:
        context.prec = 120
        std = (Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt()
        root = Decimal.from_float(float(np.sqrt(252)))
        return (
            float(root * Decimal(mean.numerator) / Decimal(mean.denominator) / std),
            float(root * std),
        )


@pytest.mark.parametrize("base", ["1", "0.1", "0.5"])
@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize("partner_dtype", ["float64", "Float64"])
def test_native_wide_excess_dispersion_matches_exact_samples(
    base: str, strict: bool, partner_dtype: str
) -> None:
    origin = np.longdouble(base)
    step = np.spacing(origin) if _WIDE else origin / 8
    strategy = pd.Series(origin + np.arange(3, dtype=np.longdouble) * step, name="return")
    benchmark = pd.Series([0, 0, 0], dtype=partner_dtype, name="return")
    before_strategy, before_benchmark = strategy.copy(deep=True), benchmark.copy(deep=True)
    expected_ir, expected_te = _oracle(strategy)
    assert not strategy.eq(strategy.iloc[0]).all()
    with np.errstate(all="raise" if strict else "ignore"):
        state = np.geterr()
        result = BenchmarkComparator().compare(strategy, benchmark)
        assert np.geterr() == state
    assert result.information_ratio == pytest.approx(expected_ir, rel=1e-12, abs=0)
    assert result.tracking_error == pytest.approx(expected_te, rel=1e-12, abs=0)
    pd.testing.assert_series_equal(result.excess_returns, strategy)
    pd.testing.assert_series_equal(strategy, before_strategy)
    pd.testing.assert_series_equal(benchmark, before_benchmark)


@pytest.mark.parametrize("dtype", ["float64", "Float64", "float32", "Float32", np.longdouble])
@pytest.mark.parametrize("value", [0.1, -0.1, 0.125])
def test_exact_constant_excess_has_zero_dispersion(dtype: object, value: float) -> None:
    strategy = pd.Series([value] * 3, dtype=dtype)
    benchmark = pd.Series([0] * 3, dtype=dtype)
    result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.excess_returns.eq(result.excess_returns.iloc[0]).all()
    assert result.information_ratio == result.tracking_error == 0


@pytest.mark.parametrize("dtype", ["uint64", "UInt64", np.longdouble])
def test_exact_maximum_unsigned_constant_excess_control(dtype: object) -> None:
    maximum = int(np.iinfo(np.uint64).max)
    strategy = pd.Series([maximum] * 3, dtype=dtype)
    benchmark = pd.Series([0] * 3, dtype=dtype)
    # ADR-273 certifies original unsigned differences; a floating source already
    # records its represented value and retains the ADR-272 constant control.
    if dtype in ("uint64", "UInt64") and np.longdouble(maximum).as_integer_ratio() != (
        maximum,
        1,
    ):
        with pytest.raises(ValueError, match=r"unsigned excess.*exactly representable"):
            BenchmarkComparator().compare(strategy, benchmark)
        return
    result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.information_ratio == result.tracking_error == 0


def test_exact_constant_excess_bypasses_std_moments_after_alignment() -> None:
    strategy = pd.Series([9, 0.1, 0.1, 0.1], index=[0, 1, 2, 3])
    benchmark = pd.Series([0, 0, 0, 8], index=[1, 2, 3, 4])
    with patch.object(pd.Series, "std", side_effect=AssertionError("unused std")):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert list(result.excess_returns.index) == [1, 2, 3]
    assert result.information_ratio == result.tracking_error == 0


def test_exact_constant_excess_of_nonconstant_sources_bypasses_std() -> None:
    strategy = pd.Series([0.125, 0.25, 0.375])
    benchmark = pd.Series([0, 0.125, 0.25])
    assert not strategy.eq(strategy.iloc[0]).all()
    assert not benchmark.eq(benchmark.iloc[0]).all()
    with patch.object(pd.Series, "std", side_effect=AssertionError("unused std")):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.beta == 1
    assert result.excess_returns.eq(0.125).all()
    assert result.information_ratio == result.tracking_error == 0


def test_native_wide_dispersion_stays_native_until_final_statistics() -> None:
    scale = np.longdouble("1e-2400") if _EXTENDED_RANGE else np.longdouble("0.125")
    strategy = pd.Series(np.arange(1, 4, dtype=np.longdouble) * scale)
    result = BenchmarkComparator().compare(strategy, pd.Series([0, 0, 0]))
    assert result.information_ratio == pytest.approx(float(np.sqrt(252) * 2), rel=1e-12)
    if _EXTENDED_RANGE:
        assert float(scale) == 0
        assert result.tracking_error == 0
    else:
        assert result.tracking_error == pytest.approx(float(np.sqrt(252) * scale))


def test_native_wide_needed_dispersion_underflow_refuses() -> None:
    if _WIDE:
        scale = np.ldexp(np.longdouble(1), np.finfo(np.longdouble).minexp // 2 - 100)
        strategy = pd.Series(np.arange(1, 4, dtype=np.longdouble) * scale)
        assert not strategy.eq(strategy.iloc[0]).all()
        with np.errstate(all="ignore"), pytest.raises(ValueError, match=r"excess.*measurable"):
            BenchmarkComparator().compare(strategy, pd.Series([0, 0, 0]))
    else:
        strategy = pd.Series([0.125, 0.25, 0.375])
        assert BenchmarkComparator().compare(strategy, pd.Series([0, 0, 0])).information_ratio > 0


@settings(max_examples=70, deadline=None)
@given(exponent=st.integers(-30, 5), n=st.integers(3, 12))
def test_native_wide_excess_dispersion_property(exponent: int, n: int) -> None:
    origin = np.ldexp(np.longdouble(1), exponent)
    step = np.spacing(origin) if _WIDE else origin / 8
    strategy = pd.Series(origin + np.arange(n, dtype=np.longdouble) * step)
    assert not strategy.eq(strategy.iloc[0]).all()
    expected_ir, expected_te = _oracle(strategy)
    result = BenchmarkComparator().compare(strategy, pd.Series([0] * n))
    assert result.information_ratio == pytest.approx(expected_ir, rel=1e-12, abs=0)
    assert result.tracking_error == pytest.approx(expected_te, rel=1e-12, abs=0)
