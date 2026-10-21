"""ADR-336: native uncertainty must be finite and positive when returned."""

import math
from fractions import Fraction
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.frontier import sharpe_standard_error

_RESULT_ERROR = "standard error must be finite and positive"
_NUMPY_OVERFLOWS = [
    (np.float16(300), 1.0),
    (np.float32(1e30), 1.0),
    (np.float64(1e200), 1.0),
    (0.0, np.float16(2.0**-24)),
    (0.0, np.float32(2.0**-149)),
    (0.0, np.float64(2.0**-1074)),
]


@pytest.mark.parametrize("score,years", _NUMPY_OVERFLOWS)
def test_numpy_overflow_cannot_return_infinite_uncertainty(score: Any, years: Any) -> None:
    with np.errstate(all="ignore"), pytest.raises(ValueError, match=_RESULT_ERROR):
        sharpe_standard_error(score, years)


@pytest.mark.parametrize("score,years", _NUMPY_OVERFLOWS)
def test_native_overflow_warning_precedes_result_refusal(score: Any, years: Any) -> None:
    with (
        np.errstate(all="warn"),
        pytest.warns(RuntimeWarning, match="overflow encountered"),
        pytest.raises(ValueError, match=_RESULT_ERROR),
    ):
        sharpe_standard_error(score, years)


@pytest.mark.parametrize("score,years", _NUMPY_OVERFLOWS)
def test_caller_raise_policy_keeps_native_exception(score: Any, years: Any) -> None:
    with np.errstate(all="raise"), pytest.raises(FloatingPointError):
        sharpe_standard_error(score, years)


def test_python_history_overflow_refuses_a_representable_exact_model_result() -> None:
    years = math.ldexp(1.0, -1074)
    # Exact independent oracle: 1/T = 2**1074, so SE = 2**537 is representable.
    exact_se = 2**537
    assert Fraction(exact_se) ** 2 * Fraction(years) == 1
    assert math.isfinite(float(exact_se))
    with pytest.raises(ValueError, match=_RESULT_ERROR):
        sharpe_standard_error(0.0, years)


@pytest.mark.parametrize("score", [1e200, 10**200, Fraction(10**200)])
def test_existing_native_overflow_exceptions_propagate(score: Any) -> None:
    with pytest.raises(OverflowError):
        sharpe_standard_error(score, 1)


@pytest.mark.parametrize("score", [0, 0.0, np.float32(1e-30), np.float64(1e-200)])
def test_zero_and_harmless_tiny_squares_keep_positive_null_uncertainty(score: Any) -> None:
    with np.errstate(all="ignore"):
        assert sharpe_standard_error(score, 4) == 0.5


@pytest.mark.parametrize("score", [504, -504, np.float32(504), Fraction(504)])
def test_supported_native_unit_closed_form_remains_exact(score: Any) -> None:
    assert sharpe_standard_error(score, 505) == 1.0


def test_history_source_guard_still_precedes_native_overflow() -> None:
    with pytest.raises(ValueError, match="holdout_years must be > 0"):
        sharpe_standard_error(np.float64(1e200), 0)


@given(
    score=st.floats(-20, 20, allow_nan=False, allow_infinity=False),
    years=st.floats(0.125, 128, allow_nan=False, allow_infinity=False),
)
def test_supported_result_matches_exact_represented_model(score: float, years: float) -> None:
    actual = sharpe_standard_error(score, years)
    exact_variance = (1 + Fraction(score) ** 2 / 504) / Fraction(years)
    assert math.isfinite(actual) and actual > 0
    assert actual == pytest.approx(math.sqrt(float(exact_variance)), rel=1e-14)
