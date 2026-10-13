"""Native zero excess means require original represented sum evidence (ADR-282)."""

import math
import sys
from fractions import Fraction
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.benchmarks import comparator
from app.research.benchmarks.comparator import BenchmarkComparator


def _oracle(excess: pd.Series, std: float) -> float:
    total = sum(Fraction(*value.as_integer_ratio()) for value in excess)
    return float(
        Fraction.from_float(float(np.sqrt(252))) * total / len(excess) / Fraction.from_float(std)
    )


def _check(actual: float, expected: float) -> None:
    if abs(expected) < sys.float_info.min:
        assert abs(
            Fraction.from_float(actual) - Fraction.from_float(expected)
        ) <= Fraction.from_float(math.ulp(0.0))
    else:
        assert actual == pytest.approx(expected, rel=1e-12, abs=0)


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
@pytest.mark.parametrize("n", [3, 4, 7, 100])
@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("exponent", [-500, -100, -70])
def test_zero_native_excess_mean_retains_original_residual(
    dtype: str, n: int, sign: int, exponent: int
) -> None:
    residual = sign * math.ldexp(1.0, exponent)
    strategy = pd.Series([0.0, residual, 2.0] + [0.0] * (n - 3), dtype=dtype, name="r")
    benchmark = pd.Series([2.0, 0.0, 0.0] + [0.0] * (n - 3), dtype=dtype, name="r")
    excess = strategy - benchmark
    assert excess.mean() == 0
    with np.errstate(under="raise"):
        std = float(excess.std())
    expected = _oracle(excess, std)
    before_s, before_b = strategy.copy(deep=True), benchmark.copy(deep=True)
    # Source log1p has its own strict-state limits for extreme public samples.
    with np.errstate(all="ignore"):
        state = np.geterr()
        result = BenchmarkComparator().compare(strategy, benchmark)
        assert np.geterr() == state
    _check(result.information_ratio, expected)
    assert np.sign(result.information_ratio) == sign
    assert result.tracking_error == float(np.sqrt(252) * std)
    pd.testing.assert_series_equal(result.excess_returns, excess)
    pd.testing.assert_series_equal(strategy, before_s)
    pd.testing.assert_series_equal(benchmark, before_b)


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
def test_true_zero_excess_sum_retains_zero_ir_and_uncertified_sum_refuses(
    dtype: str,
) -> None:
    strategy, benchmark = (
        pd.Series([0, 0, 2], dtype=dtype),
        pd.Series([2, 0, 0], dtype=dtype),
    )
    result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.information_ratio == 0
    with (
        patch(
            "app.research.benchmarks.comparator.fsum",
            side_effect=OverflowError("uncertified"),
        ),
        pytest.raises(ValueError, match=r"information ratio.*measurable"),
    ):
        BenchmarkComparator().compare(strategy, benchmark)


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
def test_certified_zero_mean_ir_direct_range_and_overflow_refusal(dtype: str) -> None:
    for sign in [-1, 1]:
        excess = pd.Series([-2.0, sign * math.ulp(0.0), 2.0], dtype=dtype)
        with np.errstate(all="raise"):
            state = np.geterr()
            actual = comparator._certified_float64_zero_mean_ir(excess, 2.0)
            assert np.geterr() == state
        assert actual == _oracle(excess, 2.0)
        assert np.sign(actual) == sign
    with pytest.raises(ValueError, match=r"information ratio.*measurable"):
        comparator._certified_float64_zero_mean_ir(
            pd.Series([sys.float_info.max] * 3, dtype=dtype), 1.0
        )


@pytest.mark.parametrize(
    "dtype", ["float64", "Float64", "float32", "Float32", "longdouble", "int64"]
)
def test_zero_mean_certification_preserves_nonzero_means_and_constants(
    dtype: str,
) -> None:
    with patch(
        "app.research.benchmarks.comparator._certified_float64_zero_mean_ir",
        create=True,
        side_effect=AssertionError("unused certification"),
    ):
        for values in [[1, 2, 3], [1, 1, 1]]:
            strategy, benchmark = (
                pd.Series(values, dtype=dtype),
                pd.Series([0] * 3, dtype=dtype),
            )
            result = BenchmarkComparator().compare(strategy, benchmark)
            assert np.isfinite(result.information_ratio)


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
def test_zero_mean_certification_retains_existing_underflow_recovery(
    dtype: str,
) -> None:
    strategy, benchmark = (
        pd.Series([1e-200, 2e-200, 3e-200], dtype=dtype),
        pd.Series([0] * 3, dtype=dtype),
    )
    with patch(
        "app.research.benchmarks.comparator._certified_float64_zero_mean_ir",
        create=True,
        side_effect=AssertionError("unused zero mean"),
    ):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.information_ratio > 0 and result.tracking_error > 0


@settings(max_examples=80, deadline=None)
@given(
    dtype=st.sampled_from(["float64", "Float64"]),
    exponent=st.integers(-500, -70),
    sign=st.sampled_from([-1, 1]),
    n=st.integers(3, 100),
    scale=st.sampled_from([2.0, 4.0, 1e50, 1e100]),
)
def test_zero_native_excess_mean_property_uses_original_sum_and_native_risk(
    dtype: str, exponent: int, sign: int, n: int, scale: float
) -> None:
    residual = sign * math.ldexp(1.0, exponent)
    strategy = pd.Series([0.0, residual, scale] + [0.0] * (n - 3), dtype=dtype)
    benchmark = pd.Series([scale, 0.0, 0.0] + [0.0] * (n - 3), dtype=dtype)
    excess = strategy - benchmark
    with np.errstate(under="raise"):
        std = float(excess.std())
    with np.errstate(all="ignore"):
        result = BenchmarkComparator().compare(strategy, benchmark)
    expected = _oracle(excess, std)
    _check(result.information_ratio, expected)
    assert np.sign(result.information_ratio) == sign
    assert result.tracking_error == float(np.sqrt(252) * std)


@pytest.mark.parametrize("dtype", ["float32", "Float32", "longdouble", "int64"])
def test_zero_mean_certification_does_not_expand_to_other_excess_types(dtype: str) -> None:
    strategy, benchmark = pd.Series([0, 0, 2], dtype=dtype), pd.Series([2, 0, 0], dtype=dtype)
    with patch(
        "app.research.benchmarks.comparator._certified_float64_zero_mean_ir",
        create=True,
        side_effect=AssertionError("unused other family"),
    ):
        result = BenchmarkComparator().compare(strategy, benchmark)
    assert result.information_ratio == 0


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
@pytest.mark.parametrize("invalid", [np.nan, np.inf, -1.0, "duplicate"])
def test_zero_mean_certification_cannot_bypass_original_source_guards(
    dtype: str, invalid: float | str
) -> None:
    strategy, benchmark = pd.Series([0, 1e-100, 2], dtype=dtype), pd.Series([2, 0, 0], dtype=dtype)
    if invalid == "duplicate":
        strategy.index = [0, 0, 2]
    else:
        strategy.iloc[1] = invalid
    with (
        patch(
            "app.research.benchmarks.comparator._certified_float64_zero_mean_ir",
            create=True,
            side_effect=AssertionError("unused invalid evidence"),
        ),
        pytest.raises(ValueError, match=r"finite|wealth|index"),
    ):
        BenchmarkComparator().compare(strategy, benchmark)
