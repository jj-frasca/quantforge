"""Original holdout validity and native predicates (ADR-301/F255/F256)."""

from dataclasses import replace
from decimal import Decimal
from fractions import Fraction

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.gate import GateConfig, GateResult, GraduationGate
from app.research.lab.holdout import HoldoutScore
from app.validation.report import ValidationReport


def _report() -> ValidationReport:
    return ValidationReport(
        strategy_name="manual",
        observed_sharpe=1.0,
        deflated_sharpe=0.5,
        pbo=0.1,
        parameter_stability_score=0.8,
        n_walk_forward_splits=0,
        n_purged_folds=0,
    )


def _evaluate(score: HoldoutScore, enabled: bool = True) -> GateResult:
    return GraduationGate().evaluate(
        _report(), 12.0, 100, score, GateConfig(require_beat_buy_and_hold=enabled)
    )


INVALID_REAL = [
    True,
    False,
    np.bool_(True),
    "1",
    None,
    complex(1),
    Decimal(1),
    float("nan"),
    float("inf"),
    float("-inf"),
    10**400,
    Fraction(10**400),
]


@pytest.mark.parametrize("field", ["sharpe", "total_return", "buy_and_hold_sharpe"])
@pytest.mark.parametrize("value", INVALID_REAL)
@pytest.mark.parametrize("enabled", [False, True])
def test_gate_invalid_original_holdout_scalar_raises(
    field: str, value: object, enabled: bool
) -> None:
    score = replace(HoldoutScore(1.0, 0.1, 252, 0.0), **{field: value})
    with pytest.raises(ValueError, match=f"holdout.{field}"):
        _evaluate(score, enabled)


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        True,
        False,
        np.bool_(True),
        None,
        "252",
        252.0,
        Fraction(252),
        Decimal(252),
        float("nan"),
        float("inf"),
    ],
)
def test_gate_invalid_original_holdout_bar_count_raises(value: object) -> None:
    with pytest.raises(ValueError, match=r"holdout\.n_bars"):
        _evaluate(HoldoutScore(1.0, 0.1, value, 0.0))  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [-1, -2.0, Fraction(-1), Fraction(-1001, 1000), np.float64(-1)])
def test_gate_original_total_return_wealth_boundary_raises(value: object) -> None:
    with pytest.raises(ValueError, match=r"holdout\.total_return"):
        _evaluate(HoldoutScore(1.0, value, 252, 0.0))  # type: ignore[arg-type]


@pytest.mark.parametrize("error", [OverflowError, ValueError, TypeError])
def test_gate_failed_original_real_float_inspection_raises_value_error(
    error: type[Exception],
) -> None:
    class BrokenFloat(float):
        def __float__(self) -> float:
            raise error("inspection failed")

    with pytest.raises(ValueError, match=r"holdout\.buy_and_hold_sharpe"):
        _evaluate(HoldoutScore(1.0, 0.1, 252, BrokenFloat(0)), False)


@pytest.mark.parametrize("count", [np.int64(252), np.uint64(252), 10**100])
def test_gate_valid_integral_count_normalizes_only_published_value(count: int) -> None:
    score = HoldoutScore(1.0, 0.1, count, 0.0)
    verdict = _evaluate(score)
    assert verdict.passed and verdict.holdout_n_bars == int(count)
    assert type(verdict.holdout_n_bars) is int and score.n_bars is count


@pytest.mark.parametrize(
    "scalar", [1, np.int64(1), np.float32(1), np.float64(1), np.longdouble(1), Fraction(1)]
)
def test_gate_valid_original_real_scalars_keep_native_inputs(scalar: object) -> None:
    score = HoldoutScore(scalar, scalar, np.int64(252), -1.0)  # type: ignore[arg-type]
    assert _evaluate(score).passed
    assert score.sharpe is scalar and score.total_return is scalar


def test_gate_original_fraction_return_above_minus_one_remains_valid() -> None:
    value = Fraction(-1) + Fraction(1, 10**400)
    assert value > -1 and float(value) == -1.0
    score = HoldoutScore(1.0, value, 252, 0.0)  # type: ignore[arg-type]
    assert _evaluate(score).passed and score.total_return is value


def test_gate_f256_tiny_exact_positive_score_projection_control_remains() -> None:
    tiny = Fraction(1, 10**400)
    score = HoldoutScore(tiny, 0.1, 252, 0)  # type: ignore[arg-type]
    assert tiny > 0 and float(tiny) == 0.0
    with pytest.raises(ValueError, match="projection"):
        _evaluate(score)
    assert score.sharpe is tiny


@pytest.mark.parametrize("stage", ["report", "count", "duration", "bars", "sharpe", "return"])
def test_gate_original_bundle_validation_preserves_precedence(stage: str) -> None:
    report = _report()
    count = 100
    duration = 12.0
    score = HoldoutScore(1.0, 0.1, 252, float("nan"))
    if stage == "report":
        report = report.model_copy(update={"observed_sharpe": float("nan")})
        expected = "observed_sharpe"
    elif stage == "count":
        count = 0
        expected = "n_trials"
    elif stage == "duration":
        duration = float("nan")
        expected = "track_record_years"
    elif stage == "bars":
        score = replace(score, n_bars=True, sharpe=True, total_return=True)
        expected = "holdout.n_bars"
    elif stage == "sharpe":
        score = replace(score, sharpe=True, total_return=True)
        expected = "holdout.sharpe"
    else:
        score = replace(score, total_return=True)
        expected = "holdout.total_return"
    with pytest.raises(ValueError, match=expected):
        GraduationGate().evaluate(report, duration, count, score, GateConfig())


def test_gate_invalid_bundle_refuses_even_when_other_component_fails() -> None:
    report = _report().model_copy(update={"deflated_sharpe": -0.5})
    with pytest.raises(ValueError, match=r"holdout\.total_return"):
        GraduationGate().evaluate(
            report, 12.0, 100, HoldoutScore(1.0, float("nan"), 252), GateConfig()
        )


@given(
    sharpe=st.floats(-100, 100, allow_nan=False, allow_infinity=False),
    benchmark=st.floats(-100, 100, allow_nan=False, allow_infinity=False),
    total_return=st.floats(-0.999, 100, allow_nan=False, allow_infinity=False),
    count=st.integers(1, 100000),
    enabled=st.booleans(),
)
def test_gate_valid_holdout_native_predicates_unchanged(
    sharpe: float, benchmark: float, total_return: float, count: int, enabled: bool
) -> None:
    verdict = _evaluate(HoldoutScore(sharpe, total_return, count, benchmark), enabled)
    assert verdict.holdout_ok == (sharpe > 0)
    assert verdict.beats_buy_and_hold_ok == (not enabled or sharpe > benchmark)
    assert verdict.passed == (sharpe > 0 and (not enabled or sharpe > benchmark))
    assert verdict.holdout_sharpe == sharpe and verdict.holdout_n_bars == count


@given(st.integers(1, 10**100), st.integers(1, 10**100))
def test_gate_valid_exact_real_controls_preserve_original_predicates(
    numerator: int, denominator: int
) -> None:
    value = Fraction(numerator, denominator)
    verdict = _evaluate(HoldoutScore(value, Fraction(-1, 2), 252, -value))  # type: ignore[arg-type]
    assert verdict.passed and verdict.holdout_ok and verdict.beats_buy_and_hold_ok
    assert verdict.holdout_sharpe == float(value)
