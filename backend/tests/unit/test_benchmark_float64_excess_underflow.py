"""Anchored float64 excess risk recovery retains the represented sample (ADR-281)."""

import math
import sys
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


def _rounded_subnormal_root(square: Fraction) -> float | None:
    unit = Fraction.from_float(math.ulp(0.0))
    squared_units = square / unit**2
    if squared_units > 2**104:
        return None
    units = math.isqrt(squared_units.numerator // squared_units.denominator)
    midpoint = Fraction(2 * units + 1, 2) ** 2
    if squared_units > midpoint or (squared_units == midpoint and units % 2):
        units += 1
    return units * math.ulp(0.0)


def _oracle(excess: pd.Series) -> tuple[float, float]:
    values = [Fraction(*value.as_integer_ratio()) for value in excess]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    assert variance > 0
    with localcontext() as context:
        context.prec = 800
        std = (Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt()
        root = Decimal.from_float(float(np.sqrt(252)))
        ir = float(root * Decimal(mean.numerator) / Decimal(mean.denominator) / std)
        te = float(root * std)
    squared_root = Fraction.from_float(float(np.sqrt(252))) ** 2
    exact_ir = _rounded_subnormal_root(squared_root * mean**2 / variance)
    exact_te = _rounded_subnormal_root(squared_root * variance)
    if exact_ir is not None:
        ir = math.copysign(exact_ir, -1 if mean < 0 else 1)
    if exact_te is not None:
        te = exact_te
    return ir, te


def _assert_statistics(
    actual: tuple[float, float], expected: tuple[float, float], *, one_ulp: bool = False
) -> None:
    for value, target in zip(actual, expected, strict=True):
        if abs(target) < sys.float_info.min:
            if one_ulp:
                assert abs(
                    Fraction.from_float(value) - Fraction.from_float(target)
                ) <= Fraction.from_float(math.ulp(0.0))
            else:
                assert value == target
        else:
            assert value == pytest.approx(target, rel=1e-12, abs=0)


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
@pytest.mark.parametrize("exponent", [-540, -600, -800, -1000])
@pytest.mark.parametrize("near_constant", [False, True])
@pytest.mark.parametrize("strict", [False, True])
def test_float64_excess_underflow_recovers_original_fraction_risk(
    dtype: str, exponent: int, near_constant: bool, strict: bool
) -> None:
    base = math.ldexp(1.0, exponent)
    values = [base, math.nextafter(base, math.inf)]
    values.append(math.nextafter(values[-1], math.inf))
    if not near_constant:
        values = [base, 2 * base, 3 * base]
    strategy, benchmark = (
        pd.Series(values, dtype=dtype),
        pd.Series([0] * 3, dtype=dtype),
    )
    before_s, before_b = strategy.copy(deep=True), benchmark.copy(deep=True)
    expected = _oracle(strategy)
    with np.errstate(all="raise" if strict else "ignore"):
        state = np.geterr()
        result = BenchmarkComparator().compare(strategy, benchmark)
        assert np.geterr() == state
    _assert_statistics((result.information_ratio, result.tracking_error), expected)
    assert result.information_ratio > 0
    assert result.tracking_error > 0
    pd.testing.assert_series_equal(result.excess_returns, strategy)
    pd.testing.assert_series_equal(strategy, before_s)
    pd.testing.assert_series_equal(benchmark, before_b)


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
@pytest.mark.parametrize("n", [2, 100, 4096])
def test_float64_subnormal_dispersion_keeps_ir_independent_of_rounded_te(
    dtype: str, n: int
) -> None:
    strategy = pd.Series([0.0] * (n - 1) + [math.ulp(0.0)], dtype=dtype)
    benchmark = pd.Series([0.0] * n, dtype=dtype)
    # Original source alpha arithmetic has its own strict-state limits.
    with np.errstate(all="ignore"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    _assert_statistics((result.information_ratio, result.tracking_error), _oracle(strategy))
    assert result.information_ratio > 0
    if n == 4096:
        assert result.tracking_error == 0


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
@pytest.mark.parametrize("sign", [-1, 0, 1])
@pytest.mark.parametrize("n", [3, 100])
def test_float64_recovery_preserves_original_signed_cancellation_sum(
    dtype: str, sign: int, n: int
) -> None:
    excess = pd.Series([-1e-200, sign * math.ulp(0.0), 1e-200] + [0.0] * (n - 3), dtype=dtype)
    with np.errstate(all="raise"):
        state = np.geterr()
        actual = comparator._recover_float64_excess_statistics(excess)
        assert np.geterr() == state
    _assert_statistics(actual, _oracle(excess))
    assert np.sign(actual[0]) == sign


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
def test_float64_recovery_declines_unmeasurable_delta_and_constant_sample(
    dtype: str,
) -> None:
    for values in [[-sys.float_info.max, sys.float_info.max], [0.1, 0.1]]:
        with pytest.raises(ValueError, match=r"excess.*measurable"):
            comparator._recover_float64_excess_statistics(pd.Series(values, dtype=dtype))


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
@pytest.mark.parametrize("values", [[0.1, 0.2, 0.3], [0.1] * 3, [1e200, 2e200, 3e200]])
def test_float64_recovery_preserves_native_paths_and_overflow_refusal(
    dtype: str, values: list[float]
) -> None:
    strategy = pd.Series(values, dtype=dtype)
    benchmark = pd.Series([0.0] * 3, dtype=dtype)
    with patch(
        "app.research.benchmarks.comparator._recover_float64_excess_statistics",
        create=True,
        side_effect=AssertionError("unused recovery"),
    ):
        if max(values) > 1e100:
            with pytest.raises(ValueError, match="finite"):
                BenchmarkComparator().compare(strategy, benchmark)
        else:
            result = BenchmarkComparator().compare(strategy, benchmark)
            std = 0.0 if len(set(values)) == 1 else float(strategy.std())
            assert result.tracking_error == float(np.sqrt(252) * std)
            assert result.information_ratio == (
                float(np.sqrt(252) * strategy.mean() / std) if std > 0 else 0.0
            )


@settings(max_examples=70, deadline=None)
@example(dtype="float64", exponent=-983, n=12, near_constant=True)
@example(dtype="Float64", exponent=-978, n=18, near_constant=True)
@given(
    dtype=st.sampled_from(["float64", "Float64"]),
    exponent=st.integers(-1000, -540),
    n=st.integers(3, 20),
    near_constant=st.booleans(),
)
def test_float64_excess_property_recovers_nonconstant_underflow(
    dtype: str, exponent: int, n: int, near_constant: bool
) -> None:
    base = math.ldexp(1.0, exponent)
    values = [base]
    for i in range(1, n):
        values.append(math.nextafter(values[-1], math.inf) if near_constant else (i + 1) * base)
    strategy, benchmark = (
        pd.Series(values, dtype=dtype),
        pd.Series([0.0] * n, dtype=dtype),
    )
    assert not strategy.eq(strategy.iloc[0]).all()
    with np.errstate(all="ignore"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    _assert_statistics(
        (result.information_ratio, result.tracking_error),
        _oracle(strategy),
        one_ulp=True,
    )
    assert result.information_ratio > 0 and result.tracking_error > 0


@pytest.mark.parametrize("units", [0, 1, 2, 112, 2**52 - 1])
def test_subnormal_risk_oracle_certifies_exact_midpoints(units: int) -> None:
    unit = Fraction.from_float(math.ulp(0.0))
    midpoint_square = (Fraction(2 * units + 1, 2) * unit) ** 2
    expected_even = units + units % 2
    assert _rounded_subnormal_root(midpoint_square) == expected_even * math.ulp(0.0)
    assert _rounded_subnormal_root(midpoint_square - unit**2 / 8) == units * math.ulp(0.0)
    assert _rounded_subnormal_root(midpoint_square + unit**2 / 8) == (units + 1) * math.ulp(0.0)
