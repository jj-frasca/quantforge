"""Mixed original integer/Float64 OLS, centered represented-input Fraction oracles."""

import math
from fractions import Fraction
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from app.research.benchmarks import comparator

_INTS = [kind + str(width) for kind in ("int", "Int", "uint", "UInt") for width in (8, 16, 32, 64)]
_FLOATS = ["float64", "Float64"]


def _fraction(value: float | int) -> Fraction:
    return (
        Fraction(int(value))
        if isinstance(value, (int, np.integer))
        else Fraction(*value.as_integer_ratio())
    )


def _oracle(a: pd.Series, b: pd.Series) -> tuple[float, float]:
    s, t = [_fraction(v) for v in a], [_fraction(v) for v in b]
    ma, mb = sum(s) / len(s), sum(t) / len(t)
    beta = Fraction(0)
    if len(set(s)) > 1 and len(set(t)) > 1:
        beta = sum((x - ma) * (y - mb) for x, y in zip(s, t, strict=True)) / sum(
            (y - mb) ** 2 for y in t
        )
    return float(beta), float(252 * (ma - beta * mb))


def _pair(
    integer: list[int], floating: list[float], dtype: str, fdtype: str, side: str
) -> tuple[pd.Series, pd.Series]:
    i, f = (
        pd.Series(integer, dtype=dtype, name="r"),
        pd.Series(floating, dtype=fdtype, name="r"),
    )
    return (i, f) if side == "strategy" else (f, i)


def _check_public(a: pd.Series, b: pd.Series) -> None:
    before_a, before_b = a.copy(deep=True), b.copy(deep=True)
    with np.errstate(all="raise"):
        state = np.geterr()
        actual = comparator.BenchmarkComparator().compare(a, b)
        assert np.geterr() == state
    aligned_a, aligned_b = a.align(b, join="inner")
    assert (actual.beta, actual.alpha) == _oracle(aligned_a, aligned_b)
    pd.testing.assert_series_equal(actual.excess_returns, aligned_a - aligned_b)
    pd.testing.assert_series_equal(a, before_a)
    pd.testing.assert_series_equal(b, before_b)


@pytest.mark.parametrize("dtype", _INTS)
@pytest.mark.parametrize("fdtype", _FLOATS)
@pytest.mark.parametrize("side", ["strategy", "benchmark"])
def test_mixed_ols_all_original_integer_widths(dtype: str, fdtype: str, side: str) -> None:
    _check_public(*_pair([0, 1, 4, 2, 7], [0.1, 0.3, 0.2, 0.7, 0.4], dtype, fdtype, side))


@pytest.mark.parametrize("dtype", ["int64", "Int64", "uint64", "UInt64"])
@pytest.mark.parametrize("fdtype", _FLOATS)
@pytest.mark.parametrize("side", ["strategy", "benchmark"])
def test_mixed_ols_large_origin_affine(dtype: str, fdtype: str, side: str) -> None:
    base = 2**60
    benchmark = [base + i * 256 for i in range(4)]
    strategy = [v + 256 for v in benchmark]
    a = pd.Series(strategy, dtype=dtype if side == "strategy" else fdtype)
    b = pd.Series(benchmark, dtype=dtype if side == "benchmark" else fdtype)
    assert _oracle(a, b) == (1.0, 64512.0)
    _check_public(a, b)


@pytest.mark.parametrize("dtype", ["int64", "Int64", "uint64", "UInt64"])
@pytest.mark.parametrize("side", ["strategy", "benchmark"])
def test_mixed_ols_original_integer_neighbors_are_not_float_encoded(dtype: str, side: str) -> None:
    a, b = _pair([2**60, 2**60 + 1, 2**60 + 2], [0.0, 1.0, 2.0], dtype, "Float64", side)
    assert len(set(a if side == "strategy" else b)) == 3
    _check_public(a, b)


@pytest.mark.parametrize("dtype", _INTS)
@pytest.mark.parametrize("side", ["strategy", "benchmark"])
@pytest.mark.parametrize("constant", ["integer", "float"])
def test_mixed_ols_constant_convention(dtype: str, side: str, constant: str) -> None:
    a, b = _pair(
        [2] * 3 if constant == "integer" else [0, 1, 2],
        [0.1] * 3 if constant == "float" else [0.1, 0.2, 0.3],
        dtype,
        "Float64",
        side,
    )
    with patch.object(pd.Series, "cov", side_effect=AssertionError("constant covariance unused")):
        result = comparator.BenchmarkComparator().compare(a, b)
    assert result.beta == 0
    assert (result.beta, result.alpha) == _oracle(a, b)


@pytest.mark.parametrize("dtype", ["int64", "Int64", "uint64", "UInt64"])
@pytest.mark.parametrize("side", ["strategy", "benchmark"])
@pytest.mark.parametrize(
    "case", ["fullwidth", "exponent_span", "tiny", "subnormal", "tie_zero", "overflow"]
)
def test_mixed_ols_helper_final_rounding(dtype: str, side: str, case: str) -> None:
    maximum = int(np.iinfo(np.int64 if dtype.lower().startswith("int") else np.uint64).max)
    tiny = math.ulp(0.0)
    integers, floats = {
        "fullwidth": ([maximum, maximum - 1, maximum - 3], [0.0, 1.0, 2.0]),
        "exponent_span": ([0, 0, 1], [0.0, tiny, np.finfo(float).max]),
        "tiny": ([0, 1, 2], [0.0, tiny, 2 * tiny]),
        "subnormal": ([0, 1], [0.0, tiny]),
        "tie_zero": ([0, 2], [0.0, tiny]),
        "overflow": ([0, 1], [0.0, tiny]),
    }[case]
    if case == "overflow" and side == "benchmark":
        integers, floats = [2**60, 2**60 + 1], [0.0, np.finfo(float).max]
    a, b = _pair(integers, floats, dtype, "Float64", side)
    if case == "overflow" or (case in {"tiny", "subnormal", "tie_zero"} and side == "strategy"):
        with pytest.raises(OverflowError):
            _oracle(a, b)
        with pytest.raises(ValueError, match=r"coefficients.*finite"):
            comparator._exact_float64_ols(a, b, constant_source=False)
    else:
        expected = _oracle(a, b)
        with np.errstate(all="raise"):
            result = comparator._exact_float64_ols(a, b, constant_source=False)
        assert result == expected
        assert [math.copysign(1, v) for v in result] == [math.copysign(1, v) for v in expected]


@pytest.mark.parametrize("side", ["strategy", "benchmark"])
def test_mixed_ols_alignment_guard_precedence(side: str) -> None:
    a, b = _pair([0, 1, 2, 3], [0.1, 0.2, 0.3, np.nan], "Int64", "Float64", side)
    a.index, b.index = [0, 1, 2, 3], [1, 2, 3, 4]
    # The float missing row lies outside overlap only for float benchmark.
    if side == "benchmark":
        a.iloc[3] = 0.4
    _check_public(a, b)
    with patch.object(
        comparator, "_exact_float64_ols", side_effect=AssertionError("guard must win")
    ):
        for source in [
            pd.Series([True, False]),
            pd.Series([1, 2], dtype=object),
            pd.Series([0.0, np.inf]),
            pd.Series([0.0, -1.0]),
            pd.Series([0, 1], index=[0, 0]),
        ]:
            with pytest.raises(ValueError):
                comparator.BenchmarkComparator().compare(source, pd.Series([0, 1], dtype="Int64"))


@settings(max_examples=60, deadline=None)
@example(dtype="UInt64", fdtype="Float64", side="strategy", values=[0, 1, 2, 3], origin=2**60)
@given(
    dtype=st.sampled_from(_INTS),
    fdtype=st.sampled_from(_FLOATS),
    side=st.sampled_from(["strategy", "benchmark"]),
    values=st.lists(st.integers(0, 12), min_size=3, max_size=10),
    origin=st.just(0),
)
def test_mixed_ols_property(
    dtype: str, fdtype: str, side: str, values: list[int], origin: int
) -> None:
    _check_public(
        *_pair(
            [origin + v for v in values],
            [0.1 + 0.03125 * v for v in values],
            dtype,
            fdtype,
            side,
        )
    )


@pytest.mark.parametrize(
    "pair",
    [
        ("float64", "Float64"),
        ("int64", "UInt64"),
        ("Float32", "Int64"),
        ("float32", "float64"),
        (np.longdouble, "Float64"),
    ],
)
def test_mixed_ols_preserves_predecessor_and_other_families(
    pair: tuple[object, object],
) -> None:
    a, b = pd.Series([0, 1, 2], dtype=pair[0]), pd.Series([0, 2, 1], dtype=pair[1])
    if pair in (("float64", "Float64"), ("float32", "float64")):
        # ADR-285 admits narrow/Float64 while preserving both-Float64 routing.
        with patch.object(
            comparator, "_exact_float64_ols", wraps=comparator._exact_float64_ols
        ) as exact_ols:
            result = comparator.BenchmarkComparator().compare(a, b)
        assert exact_ols.call_count == 1
    else:
        with patch.object(
            comparator,
            "_exact_float64_ols",
            side_effect=AssertionError("outside exact family"),
        ):
            result = comparator.BenchmarkComparator().compare(a, b)
    assert (result.beta, result.alpha) == _oracle(a, b)
    assert result.information_ratio == 0.0
    assert result.tracking_error == float(np.sqrt(252))
    if pair == ("int64", "UInt64") or pair == (np.longdouble, "Float64"):
        expected_excess = pd.Series([0, -1, 1], dtype=np.longdouble)
    else:
        expected_excess = a - b
    pd.testing.assert_series_equal(result.excess_returns, expected_excess)


@pytest.mark.parametrize("side", ["strategy", "benchmark"])
def test_mixed_ols_constant_final_overflow(side: str) -> None:
    a, b = _pair([1, 1], [np.finfo(float).max] * 2, "UInt64", "Float64", side)
    if side == "benchmark":
        with pytest.raises(OverflowError):
            _oracle(a, b)
        with pytest.raises(ValueError, match=r"coefficients.*finite"):
            comparator._exact_float64_ols(a, b, constant_source=True)
        with pytest.raises(ValueError):
            comparator.BenchmarkComparator().compare(a, b)
    else:
        assert comparator._exact_float64_ols(a, b, constant_source=True) == (0.0, 252.0)
