"""ADR-298: native arithmetic failure is not a measured MinBTL requirement."""

import math
import warnings
from fractions import Fraction
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.gate import minbtl_years


@pytest.mark.parametrize(
    "score",
    [
        1e160,
        1e200,
        1e-200,
        1e-160,
        np.float64(1e160),
        np.float64(1e-200),
        np.float64(1e-160),
        np.longdouble("1e200"),
        Fraction(1, 10**200),
        np.int64(3037000500),
        np.int64(2**32),
        np.int64(2**32 + 1),
        np.int64(np.iinfo(np.int64).max),
        np.uint64(2**32),
        np.uint64(2**32 + 1),
        np.uint64(np.iinfo(np.uint64).max),
    ],
)
@pytest.mark.parametrize("count", [1, 2])
@pytest.mark.parametrize("policy", ["ignore", "warn", "raise"])
def test_minbtl_unmeasurable_native_square_or_result_refuses_and_preserves_caller_policy(
    score: Any, count: int, policy: str
) -> None:
    with np.errstate(all=policy), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        before = np.geterr().copy()
        try:
            # N=1 avoids quotient overflow, but NumPy's strict underflow policy
            # still refuses its subnormal square. Python arithmetic ignores that policy.
            if (
                count == 1
                and float(score) == 1e-160
                and (not isinstance(score, np.floating) or policy != "raise")
            ):
                assert minbtl_years(count, score) == 0.0
            else:
                with pytest.raises(ValueError, match="MinBTL"):
                    minbtl_years(count, score)
        finally:
            assert np.geterr() == before


@pytest.mark.parametrize("policy", ["ignore", "warn", "raise"])
def test_minbtl_preserves_numpy_overflow_warning_policy(policy: str) -> None:
    with np.errstate(over=policy), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", RuntimeWarning)
        before = np.geterr().copy()
        with pytest.raises(ValueError, match="MinBTL"):
            minbtl_years(2, np.float64(1e160))
        assert np.geterr() == before
        assert bool(caught) == (policy == "warn")


@pytest.mark.parametrize("policy", ["ignore", "warn", "raise"])
def test_minbtl_native_quotient_overflow_refuses_after_a_measurable_square(policy: str) -> None:
    score = np.float32(2e-19)
    with np.errstate(all=policy), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", RuntimeWarning)
        before = np.geterr().copy()
        # The float32 square is normal and measurable, but 2*ln(10000)/square
        # exceeds float32's range. Raise policy therefore reaches division's handler.
        assert float(score**2) > np.finfo(np.float32).tiny
        with pytest.raises(ValueError, match="MinBTL"):
            minbtl_years(10000, score)
        assert np.geterr() == before
        assert bool(caught) == (policy == "warn")


@pytest.mark.parametrize(
    "score",
    [
        np.int64(3037000499),
        np.uint64(2**32 - 1),
        np.float64(0.1),
        np.float32(0.1),
        np.longdouble("0.1"),
        Fraction(1, 10),
        1.5,
    ],
)
@pytest.mark.parametrize("count", [1, 2, 10**400])
@pytest.mark.parametrize("policy", ["ignore", "warn", "raise"])
def test_minbtl_safe_original_native_arithmetic_is_exactly_retained(
    score: Any, count: int, policy: str
) -> None:
    with np.errstate(all=policy):
        before = np.geterr().copy()
        expected = 2.0 * math.log(count) / (score**2)
        assert minbtl_years(count, score) == expected
        assert np.geterr() == before


@given(
    value=st.integers(min_value=1, max_value=np.iinfo(np.int64).max),
    count=st.integers(min_value=1, max_value=10**12),
)
def test_minbtl_integral_squares_are_mathematical_or_refused(value: int, count: int) -> None:
    original = np.int64(value)
    exact_square = value * value
    with np.errstate(all="ignore"):
        if exact_square > np.iinfo(np.int64).max:
            with pytest.raises(ValueError, match="MinBTL"):
                minbtl_years(count, original)
        else:
            assert minbtl_years(count, original) == 2.0 * math.log(count) / exact_square
