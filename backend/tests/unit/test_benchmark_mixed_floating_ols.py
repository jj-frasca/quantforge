"""Mixed narrow/Float64 coefficients from original represented observations."""

import math
from fractions import Fraction
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from app.research.benchmarks import comparator

_NARROW = ["float16", "float32", "Float32"]
_FLOATS = ["float64", "Float64"]


def _oracle(a: pd.Series, b: pd.Series) -> tuple[float, float]:
    s = [Fraction(*v.as_integer_ratio()) for v in a]
    t = [Fraction(*v.as_integer_ratio()) for v in b]
    ma, mb = sum(s) / len(s), sum(t) / len(t)
    beta = Fraction(0)
    if len(set(s)) > 1 and len(set(t)) > 1:
        beta = sum((x - ma) * (y - mb) for x, y in zip(s, t, strict=True)) / sum(
            (y - mb) ** 2 for y in t
        )
    return float(beta), float(252 * (ma - beta * mb))


def _pair(
    narrow: list[float] | np.ndarray,
    wide: list[float] | np.ndarray,
    dtype: str,
    fdtype: str,
    side: str,
) -> tuple[pd.Series, pd.Series]:
    x, y = (
        pd.Series(narrow, dtype=dtype, name="r"),
        pd.Series(wide, dtype=fdtype, name="r"),
    )
    return (x, y) if side == "strategy" else (y, x)


def _check(a: pd.Series, b: pd.Series) -> None:
    aa, bb = a.copy(deep=True), b.copy(deep=True)
    with np.errstate(all="raise"):
        state = np.geterr()
        result = comparator.BenchmarkComparator().compare(a, b)
        assert np.geterr() == state
    aligned_a, aligned_b = a.align(b, join="inner")
    assert (result.beta, result.alpha) == _oracle(aligned_a, aligned_b)
    pd.testing.assert_series_equal(result.excess_returns, aligned_a - aligned_b)
    pd.testing.assert_series_equal(a, aa)
    pd.testing.assert_series_equal(b, bb)


@pytest.mark.parametrize("dtype", _NARROW)
@pytest.mark.parametrize("fdtype", _FLOATS)
@pytest.mark.parametrize("side", ["strategy", "benchmark"])
@pytest.mark.parametrize("n", [3, 4, 7])
def test_mixed_floating_ols_original_half_ulp_intercept(
    dtype: str, fdtype: str, side: str, n: int
) -> None:
    native = np.float16 if dtype == "float16" else np.float32
    base = native(2**10 if dtype == "float16" else 2**60)
    values = base + np.arange(n, dtype=native) * np.spacing(base)
    offset = float(np.spacing(base)) / 2
    counterpart = values.astype(float) + (offset if side == "benchmark" else -offset)
    a, b = _pair(values, counterpart, dtype, fdtype, side)
    assert _oracle(a, b) == (1.0, 252 * offset)
    _check(a, b)


@pytest.mark.parametrize("dtype", ["float32", "Float32"])
@pytest.mark.parametrize("fdtype", _FLOATS)
@pytest.mark.parametrize("side", ["strategy", "benchmark"])
def test_mixed_floating_ols_coupled_slope_and_intercept(dtype: str, fdtype: str, side: str) -> None:
    narrow = np.float32(2**60) + np.arange(4, dtype=np.float32) * 2**37
    wide = float(2**60) + np.arange(4) * 256
    a, b = _pair(narrow, wide, dtype, fdtype, side)
    assert _oracle(a, b)[0] == (2**29 if side == "strategy" else 2**-29)
    _check(a, b)


@pytest.mark.parametrize("dtype", _NARROW)
@pytest.mark.parametrize("fdtype", _FLOATS)
@pytest.mark.parametrize("side", ["strategy", "benchmark"])
@pytest.mark.parametrize("constant", ["narrow", "float64"])
def test_mixed_floating_ols_constants(dtype: str, fdtype: str, side: str, constant: str) -> None:
    a, b = _pair(
        [0.1] * 3 if constant == "narrow" else [0.1, 0.2, 0.3],
        [0.1] * 3 if constant == "float64" else [0.1, 0.2, 0.3],
        dtype,
        fdtype,
        side,
    )
    with patch.object(pd.Series, "cov", side_effect=AssertionError("unused constant covariance")):
        _check(a, b)


@pytest.mark.parametrize("dtype", _NARROW)
@pytest.mark.parametrize("fdtype", _FLOATS)
@pytest.mark.parametrize("side", ["strategy", "benchmark"])
@pytest.mark.parametrize("case", ["exponent_span", "subnormal", "tie_zero", "tiny"])
def test_mixed_floating_ols_helper_final_rounding(
    dtype: str, fdtype: str, side: str, case: str
) -> None:
    tiny = math.ulp(0.0)
    narrow, wide = {
        "exponent_span": ([0.0, 0.0, 1.0], [0.0, tiny, np.finfo(float).max]),
        "subnormal": ([0.0, 1.0], [0.0, tiny]),
        "tie_zero": ([0.0, 2.0], [0.0, tiny]),
        "tiny": ([0.0, 1.0, 2.0], [0.0, tiny, 2 * tiny]),
    }[case]
    a, b = _pair(narrow, wide, dtype, fdtype, side)
    if case != "exponent_span" and side == "strategy":
        with pytest.raises(OverflowError):
            _oracle(a, b)
        with pytest.raises(ValueError, match=r"coefficients.*finite"):
            comparator._exact_float64_ols(a, b, constant_source=False)
    else:
        expected = _oracle(a, b)
        with np.errstate(all="raise"):
            actual = comparator._exact_float64_ols(a, b, constant_source=False)
        assert actual == expected
        assert [math.copysign(1, x) for x in actual] == [math.copysign(1, x) for x in expected]


@pytest.mark.parametrize("dtype", _NARROW)
@pytest.mark.parametrize("side", ["strategy", "benchmark"])
def test_mixed_floating_ols_alignment_and_guard_precedence(dtype: str, side: str) -> None:
    a, b = _pair([0.1, 0.2, 0.3, 0.4], [0.2, 0.3, 0.4, 0.5], dtype, "Float64", side)
    a.index, b.index = [0, 1, 2, 3], [1, 2, 3, 4]
    _check(a, b)
    for invalid in (np.nan, np.inf, -1.0):
        bad = a.copy()
        bad.iloc[2] = invalid
        with (
            patch.object(
                comparator,
                "_exact_float64_ols",
                side_effect=AssertionError("guard must precede coefficients"),
            ),
            pytest.raises(ValueError),
        ):
            comparator.BenchmarkComparator().compare(bad, b)


@settings(max_examples=60, deadline=None)
@example(dtype="Float32", fdtype="Float64", side="strategy", values=[0, 1, 2, 3])
@given(
    dtype=st.sampled_from(_NARROW),
    fdtype=st.sampled_from(_FLOATS),
    side=st.sampled_from(["strategy", "benchmark"]),
    values=st.lists(st.integers(0, 20), min_size=3, max_size=10),
)
def test_mixed_floating_ols_property(dtype: str, fdtype: str, side: str, values: list[int]) -> None:
    _check(
        *_pair(
            [v / 32 for v in values],
            [0.1 + v / 64 for v in values],
            dtype,
            fdtype,
            side,
        )
    )


@pytest.mark.parametrize(
    "pair",
    [
        ("float16", "float32"),
        ("Float32", "Float32"),
        ("Int64", "float16"),
        ("UInt64", "Float32"),
        (np.longdouble, "Float64"),
        ("int64", "UInt64"),
    ],
)
def test_mixed_floating_ols_outside_helper_bypass(pair: tuple[object, object]) -> None:
    a, b = pd.Series([0, 1, 2], dtype=pair[0]), pd.Series([0, 2, 1], dtype=pair[1])
    with patch.object(
        comparator,
        "_exact_float64_ols",
        side_effect=AssertionError("outside coupled family"),
    ):
        result = comparator.BenchmarkComparator().compare(a, b)
    assert (result.beta, result.alpha) == (0.5, 126.0)


@pytest.mark.parametrize(
    "pair", [("float64", "Float64"), ("Int64", "float64"), ("Float64", "UInt64")]
)
def test_mixed_floating_ols_predecessor_exact_coefficients(
    pair: tuple[object, object],
) -> None:
    a, b = pd.Series([0, 1, 2], dtype=pair[0]), pd.Series([0, 2, 1], dtype=pair[1])
    with patch.object(
        comparator, "_exact_float64_ols", wraps=comparator._exact_float64_ols
    ) as helper:
        result = comparator.BenchmarkComparator().compare(a, b)
    assert helper.call_count == 1
    assert (result.beta, result.alpha) == (0.5, 126.0)
