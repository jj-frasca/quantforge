"""ADR-335: native integral square evidence must match exact integer arithmetic."""

import math
from fractions import Fraction
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.frontier import sharpe_standard_error

_WRAP_ERROR = "integral Sharpe square"


@pytest.mark.parametrize("mode", ["ignore", "warn", "raise"])
@pytest.mark.parametrize(
    "score",
    [
        np.int8(12),
        np.int8(-12),
        np.int8(16),
        np.int8(-16),
        np.int8(100),
        np.int8(-100),
        np.uint8(16),
        np.uint8(20),
        np.int64(3037000500),
        np.int64(-3037000500),
        np.int64(2**32),
        np.int64(-(2**32)),
        np.uint64(2**32),
        np.uint64(2**32 + 1),
        np.uint64(2**64 - 1),
    ],
)
def test_positive_negative_and_zero_wrapped_squares_refuse(score: Any, mode: str) -> None:
    # Independent mathematical witness, regardless of the sign of the wrapped square.
    with np.errstate(all=mode):
        assert int(score**2) != int(score) ** 2
        with pytest.raises(ValueError, match=_WRAP_ERROR):
            sharpe_standard_error(score, 1)


@pytest.mark.parametrize(
    "score",
    [
        0,
        10**100,
        np.int8(0),
        np.int8(11),
        np.int8(-11),
        np.uint8(0),
        np.uint8(15),
        np.int64(0),
        np.int64(3037000499),
        np.int64(-3037000499),
        np.uint64(0),
        np.uint64(2**32 - 1),
    ],
)
def test_safe_integral_squares_preserve_native_formula_exactly(score: Any) -> None:
    with np.errstate(all="raise"):
        expected = math.sqrt((1.0 + score**2 / 504.0) / Fraction(1, 2))
        assert sharpe_standard_error(score, Fraction(1, 2)) == expected
        assert sharpe_standard_error(score, 1) == pytest.approx(
            math.sqrt(float(1 + Fraction(int(score) ** 2, 504)))
        )


class _NonintegralSquare(int):
    """An accepted original Integral whose derived operator changes its type."""

    def __new__(cls, square: Any) -> "_NonintegralSquare":
        instance = super().__new__(cls, 3)
        instance.square = square
        return instance

    def __pow__(self, exponent: Any, modulo: Any = None) -> Any:
        assert exponent == 2 and modulo is None
        return self.square


@pytest.mark.parametrize("square", [9.5, Fraction(19, 2), 9.0, Fraction(9)])
def test_nonintegral_native_square_refuses_before_truncation(square: Any) -> None:
    score = _NonintegralSquare(square)
    assert int(score**2) == int(score) ** 2
    with pytest.raises(ValueError, match=_WRAP_ERROR):
        sharpe_standard_error(score, 1)


def test_original_history_guard_precedes_wrapped_square() -> None:
    with pytest.raises(ValueError, match="holdout_years must be > 0"):
        sharpe_standard_error(np.int8(100), 0)


@pytest.mark.parametrize("score", [0.0, np.float32(1e-30), np.float64(1e-200), Fraction(1, 3)])
def test_nonintegral_score_retains_null_underflow_and_native_arithmetic(score: Any) -> None:
    with np.errstate(all="ignore"):
        expected = math.sqrt((1.0 + score**2 / 504.0) / 4)
        assert sharpe_standard_error(score, 4) == expected
        assert expected > 0


def test_python_native_square_overflow_still_propagates() -> None:
    with pytest.raises(OverflowError):
        sharpe_standard_error(1e200, 1)


def test_caller_numpy_raise_policy_still_propagates() -> None:
    with np.errstate(all="raise"), pytest.raises(FloatingPointError):
        sharpe_standard_error(np.float64(1e200), 1)


@st.composite
def _integral_scores(draw: st.DrawFn) -> Any:
    dtype = draw(
        st.sampled_from(
            [np.int8, np.uint8, np.int16, np.uint16, np.int32, np.uint32, np.int64, np.uint64]
        )
    )
    limits = np.iinfo(dtype)
    return dtype(draw(st.integers(int(limits.min), int(limits.max))))


@given(score=_integral_scores(), years=st.integers(1, 20))
def test_native_integer_square_integrity_matches_exact_oracle(score: Any, years: int) -> None:
    with np.errstate(all="raise"):
        exact_square = int(score) ** 2
        native_square = score**2
        if int(native_square) != exact_square:
            with pytest.raises(ValueError, match=_WRAP_ERROR):
                sharpe_standard_error(score, years)
        else:
            actual = sharpe_standard_error(score, years)
            assert actual == math.sqrt((1.0 + native_square / 504.0) / years)
            assert actual == pytest.approx(
                math.sqrt(float((1 + Fraction(exact_square, 504)) / years))
            )
