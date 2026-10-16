"""ADR-297: original MinBTL score validity precedes shortcuts without normalization."""

import math
from decimal import Decimal
from fractions import Fraction
from typing import Any

import numpy as np
import pytest

from app.research.lab.gate import minbtl_years


@pytest.mark.parametrize(
    "score",
    [
        True,
        False,
        np.bool_(True),
        np.bool_(False),
        math.nan,
        math.inf,
        -math.inf,
        np.float64(math.nan),
        np.float64(math.inf),
        np.float64(-math.inf),
        np.array(1.0),
        np.array([1.0]),
        np.array(-1.0),
        [1.0],
        "1",
        Decimal(1),
        1 + 0j,
        None,
        10**400,
        -(10**400),
        Fraction(10**400),
    ],
)
@pytest.mark.parametrize("count", [1, 2, 100])
def test_minbtl_invalid_original_score_refuses_before_shortcuts(score: Any, count: int) -> None:
    with pytest.raises(ValueError, match="annualized_sharpe"):
        minbtl_years(count, score)


@pytest.mark.parametrize("count", [True, 0, -1, 1.0])
def test_minbtl_invalid_count_retains_precedence_over_invalid_score(count: Any) -> None:
    with pytest.raises(ValueError, match="n_trials"):
        minbtl_years(count, math.nan)


@pytest.mark.parametrize(
    "score",
    [0, 0.0, -0.0, -1.0, np.float32(-0.5), np.int64(-1), Fraction(-1, 10**400)],
)
@pytest.mark.parametrize("count", [1, 100])
def test_minbtl_nonpositive_finite_original_score_keeps_infinite_requirement(
    score: Any, count: int
) -> None:
    assert minbtl_years(count, score) == math.inf


@pytest.mark.parametrize("score", [1, 0.1, 1.5, np.int64(2), np.float32(0.1), np.float64(1.5)])
@pytest.mark.parametrize("count", [1, 100, 10**400])
def test_minbtl_finite_native_score_retains_exact_existing_arithmetic(
    score: Any, count: int
) -> None:
    expected = 2.0 * math.log(count) / (score**2)
    assert minbtl_years(count, score) == expected


def test_minbtl_fraction_score_is_not_replaced_by_its_float_projection() -> None:
    score = Fraction(1, 10)
    expected = 2.0 * math.log(100) / Fraction(1, 100)
    normalized = 2.0 * math.log(100) / float(score) ** 2
    assert expected != normalized
    assert minbtl_years(100, score) == expected
