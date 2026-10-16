"""ADR-296: available history is original finite scalar evidence, not an infinite requirement."""

import math
from decimal import Decimal
from fractions import Fraction
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.gate import GateConfig, GraduationGate, minbtl_years
from app.research.lab.holdout import HoldoutScore
from app.validation.report import ValidationReport


def report(observed: float = 1.0) -> ValidationReport:
    return ValidationReport(
        strategy_name="manual",
        observed_sharpe=observed,
        deflated_sharpe=0.5,
        pbo=0.1,
        parameter_stability_score=0.8,
        n_walk_forward_splits=0,
        n_purged_folds=0,
    )


def evaluate(duration: Any, count: int = 100, observed: float = 1.0) -> Any:
    return GraduationGate().evaluate(
        report(observed), duration, count, HoldoutScore(1.0, 0.1, 252, 0.2), GateConfig()
    )


@pytest.mark.parametrize(
    "duration",
    [
        math.inf,
        -math.inf,
        math.nan,
        np.float64(math.inf),
        True,
        False,
        np.bool_(True),
        np.bool_(False),
        np.array(12.0),
        np.array([12.0]),
        [12.0],
        "12",
        Decimal(12),
        12 + 0j,
        None,
        -1.0,
        Fraction(-1, 10**400),
        10**400,
        Fraction(10**400),
    ],
)
@pytest.mark.parametrize("observed", [1.0, 0.0, -1.0])
def test_gate_invalid_original_duration_refuses_without_a_verdict(
    duration: Any, observed: float
) -> None:
    with pytest.raises(ValueError, match="track_record_years"):
        evaluate(duration, observed=observed)


@pytest.mark.parametrize("duration", [0, 0.0, -0.0, Fraction(0), np.float64(-0.0), np.int64(0)])
def test_gate_zero_duration_retains_single_trial_boundary(duration: Any) -> None:
    assert evaluate(duration, count=1).passed
    assert not evaluate(duration, count=2).mintrl_ok


@pytest.mark.parametrize("observed", [0.0, -1.0])
@pytest.mark.parametrize("duration", [0, 12.0, Fraction(1000), np.finfo(float).max])
def test_gate_finite_available_history_cannot_satisfy_infinite_requirement(
    observed: float, duration: Any
) -> None:
    result = evaluate(duration, observed=observed)
    assert result.required_track_record_years == math.inf
    assert not result.mintrl_ok
    assert not result.passed


@pytest.mark.parametrize("duration", [12, 12.0, Fraction(12), np.int64(12), np.float64(12)])
def test_gate_valid_duration_representations_retain_exact_result(duration: Any) -> None:
    assert evaluate(duration).model_dump() == evaluate(12.0).model_dump()


def test_gate_duration_comparison_retains_original_fraction_boundary() -> None:
    required = minbtl_years(100, 1.0)
    exact = Fraction.from_float(required)
    epsilon = Fraction(1, 10**100)
    assert float(exact - epsilon) == float(exact + epsilon) == required
    assert not evaluate(exact - epsilon).mintrl_ok
    assert evaluate(exact).mintrl_ok
    assert evaluate(exact + epsilon).mintrl_ok


def test_gate_report_revalidation_precedes_duration_guard() -> None:
    invalid = report().model_copy(update={"pbo": math.nan})
    with pytest.raises(ValueError, match="pbo"):
        GraduationGate().evaluate(
            invalid, math.inf, 100, HoldoutScore(1.0, 0.1, 252, 0.2), GateConfig()
        )


def test_gate_original_trial_count_precedes_duration_guard() -> None:
    with pytest.raises(ValueError, match="n_trials"):
        evaluate(math.inf, count=True)


@given(
    count=st.integers(min_value=1, max_value=10**6),
    observed=st.floats(min_value=0.1, max_value=10, allow_nan=False, allow_infinity=False),
    first=st.floats(min_value=0, max_value=10**6, allow_nan=False, allow_infinity=False),
    second=st.floats(min_value=0, max_value=10**6, allow_nan=False, allow_infinity=False),
)
def test_gate_valid_duration_matches_original_requirement_and_is_monotone(
    count: int, observed: float, first: float, second: float
) -> None:
    low, high = sorted((first, second))
    required = 2 * math.log(count) / observed**2
    lower = evaluate(low, count, observed)
    upper = evaluate(high, count, observed)
    assert lower.mintrl_ok == (low >= required)
    assert upper.mintrl_ok == (high >= required)
    assert not lower.passed or upper.passed
