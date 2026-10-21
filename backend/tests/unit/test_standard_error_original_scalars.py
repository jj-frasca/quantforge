"""ADR-334: inspect original SE evidence without replacing native operands."""

import math
from decimal import Decimal
from fractions import Fraction
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.frontier import sharpe_standard_error


@pytest.mark.parametrize("parameter", ["sharpe", "holdout_years"])
@pytest.mark.parametrize(
    "bad",
    [
        True,
        False,
        np.bool_(True),
        "1",
        1 + 0j,
        Decimal("1"),
        None,
        [1],
        np.array(1),
        np.array([1]),
        math.nan,
        math.inf,
        -math.inf,
        np.float64(math.nan),
        pytest.param(10**400, id="huge-int"),
    ],
)
def test_original_nonfinite_or_nonreal_scalars_refuse(parameter: str, bad: Any) -> None:
    args = {"sharpe": 1.0, "holdout_years": 1.0}
    args[parameter] = bad
    with np.errstate(all="ignore"), pytest.raises(ValueError, match=parameter):
        sharpe_standard_error(**args)


@pytest.mark.parametrize("years", [0, -1, Fraction(-1, 10**400), np.float32(-1)])
def test_original_nonpositive_history_still_precedes_score_validation(years: Any) -> None:
    with pytest.raises(ValueError, match="holdout_years must be > 0"):
        sharpe_standard_error(math.nan, years)


def test_history_original_domain_precedes_malformed_score() -> None:
    with pytest.raises(ValueError, match="holdout_years"):
        sharpe_standard_error("bad", math.inf)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "score", [504, -504, 504.0, np.int64(504), np.float32(-504), Fraction(504)]
)
def test_valid_original_families_retain_the_unit_closed_form(score: Any) -> None:
    # Exact model: (1 + 504**2/504)/505 = 1.
    assert sharpe_standard_error(score, 505) == 1.0


@pytest.mark.parametrize(
    "years,expected",
    [
        (4, 0.5),
        (Fraction(1, 4), 2.0),
        (np.float32(4), 0.5),
        (np.float64(4), 0.5),
    ],
)
def test_zero_score_retains_the_null_standard_error(years: Any, expected: float) -> None:
    assert sharpe_standard_error(0, years) == expected


def test_safe_native_integer_arithmetic_is_not_replaced() -> None:
    # An int8 square of 4 fits; no score normalization is needed.
    actual = sharpe_standard_error(np.int8(4), Fraction(1, 2))
    assert actual == pytest.approx(math.sqrt(float(Fraction(130, 63))))


@given(
    score=st.floats(-20, 20, allow_nan=False, allow_infinity=False),
    years=st.floats(0.1, 100, allow_nan=False, allow_infinity=False),
)
def test_signed_symmetry_and_fourfold_history_scaling(score: float, years: float) -> None:
    original = sharpe_standard_error(score, years)
    assert original == sharpe_standard_error(-score, years)
    assert sharpe_standard_error(score, 4 * years) == pytest.approx(original / 2)
