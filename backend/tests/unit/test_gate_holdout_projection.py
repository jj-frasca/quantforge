"""ADR-309: native holdout verdicts must survive their published projection."""

from fractions import Fraction
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.gate import GateConfig, GateResult, GraduationGate
from app.research.lab.holdout import HoldoutScore
from app.validation.report import ValidationReport


def _evaluate(
    sharpe: Any,
    benchmark: Any = 0.0,
    *,
    floor: float = 0.0,
    enabled: bool = True,
    other_passes: bool = True,
    total_return: Any = 0.1,
    count: Any = 252,
) -> GateResult:
    report = ValidationReport(
        strategy_name="manual",
        observed_sharpe=1.0,
        deflated_sharpe=0.5 if other_passes else -0.5,
        pbo=0.1,
        parameter_stability_score=0.8,
        n_walk_forward_splits=0,
        n_purged_folds=0,
    )
    return GraduationGate().evaluate(
        report,
        12.0,
        100,
        HoldoutScore(sharpe, total_return, count, benchmark),
        GateConfig(holdout_sharpe_min=floor, require_beat_buy_and_hold=enabled),
    )


@pytest.mark.parametrize("other_passes", [False, True])
@pytest.mark.parametrize(
    ("sharpe", "benchmark", "floor"),
    [
        (Fraction(1, 10**400), 0.0, 0.0),
        (Fraction(1) + Fraction(1, 10**100), 0.0, 1.0),
        (Fraction(1) + Fraction(1, 10**100), Fraction(1), 0.0),
        (np.float32(0.1), 0.0, 0.1),
        (np.float32(0.1), 0.1, 0.0),
    ],
)
def test_gate_verdict_changing_projection_raises_before_publication(
    sharpe: Any, benchmark: Any, floor: float, other_passes: bool
) -> None:
    native = (bool(sharpe > floor), bool(sharpe > benchmark))
    projected = (float(sharpe) > floor, float(sharpe) > float(benchmark))
    assert native != projected
    with pytest.raises(ValueError, match="projection"):
        _evaluate(sharpe, benchmark, floor=floor, other_passes=other_passes)


def test_gate_numpy_wider_boundary_obeys_actual_native_projection_contract() -> None:
    # longdouble precision is platform-dependent; exercise the actual relationship,
    # without skipping the boundary on platforms where it equals binary64.
    value = np.nextafter(np.longdouble(1), np.longdouble(2))
    native, projected = bool(value > 1.0), float(value) > 1.0
    if native != projected:
        assert native and not projected
        with pytest.raises(ValueError, match="projection"):
            _evaluate(value, floor=1.0)
    else:
        result = _evaluate(value, floor=1.0)
        assert result.holdout_ok == native
        assert result.holdout_sharpe == float(value)


def test_gate_numpy32_false_to_true_projection_is_refused_without_redeciding() -> None:
    value = np.float32(0.1)
    assert not (value > 0.1) and float(value) > 0.1
    with pytest.raises(ValueError, match="projection"):
        _evaluate(value, floor=0.1)


@pytest.mark.parametrize(
    ("value", "benchmark"),
    [
        (Fraction(1) + Fraction(1, 10**100), Fraction(1)),
        (np.float32(0.1), 0.1),
    ],
)
def test_gate_disabled_benchmark_does_not_require_unused_order_coherence(
    value: Any, benchmark: Any
) -> None:
    assert bool(value > benchmark) != (float(value) > float(benchmark))
    result = _evaluate(value, benchmark, enabled=False)
    assert result.passed and result.beats_buy_and_hold_ok
    assert result.holdout_sharpe == float(value)


@pytest.mark.parametrize("enabled", [False, True])
def test_gate_holdout_projection_guard_remains_active_with_benchmark_disabled(
    enabled: bool,
) -> None:
    with pytest.raises(ValueError, match="projection"):
        _evaluate(Fraction(1, 10**400), enabled=enabled)


@pytest.mark.parametrize("sharpe", [0.0, -0.0, 1.0, -1.0])
@pytest.mark.parametrize("enabled", [False, True])
def test_gate_coherent_equalities_keep_original_strict_verdicts(
    sharpe: float, enabled: bool
) -> None:
    result = _evaluate(sharpe, sharpe, floor=sharpe, enabled=enabled)
    assert not result.passed and not result.holdout_ok
    assert result.beats_buy_and_hold_ok == (not enabled)


@pytest.mark.parametrize("direction", [-np.inf, np.inf])
@pytest.mark.parametrize("floor", [-1.0, 0.0, 1.0])
def test_gate_binary64_threshold_neighbors_keep_native_verdicts(
    direction: float, floor: float
) -> None:
    value = float(np.nextafter(floor, direction))
    result = _evaluate(value, -2.0, floor=floor)
    assert result.holdout_ok == (value > floor)
    assert result.beats_buy_and_hold_ok == (value > -2.0)
    assert result.holdout_sharpe == value


@pytest.mark.parametrize(
    "value", [Fraction(1, 3), np.float32(0.25), np.float64(0.25), np.longdouble(0.25), 1]
)
def test_gate_coherent_numeric_families_publish_checked_float_without_mutation(value: Any) -> None:
    score = HoldoutScore(value, Fraction(-1) + Fraction(1, 10**400), 10**100, -1.0)
    config = GateConfig()
    original = (score.sharpe, score.total_return, score.n_bars, score.buy_and_hold_sharpe)
    report = ValidationReport(
        strategy_name="manual",
        observed_sharpe=1.0,
        deflated_sharpe=0.5,
        pbo=0.1,
        parameter_stability_score=0.8,
        n_walk_forward_splits=0,
        n_purged_folds=0,
    )
    config_before = config.model_dump()
    result = GraduationGate().evaluate(report, 12.0, 100, score, config)
    assert result.passed and type(result.holdout_sharpe) is float
    assert result.holdout_sharpe == float(value) and result.holdout_n_bars == 10**100
    assert type(result.holdout_n_bars) is int
    assert score.sharpe is original[0] and score.total_return is original[1]
    assert score.n_bars is original[2] and score.buy_and_hold_sharpe is original[3]
    assert score.total_return > -1 and float(score.total_return) == -1.0
    assert config.model_dump() == config_before


@given(st.integers(1, 100000), st.integers(1, 100000))
def test_gate_lossy_same_side_fraction_projection_remains_valid(
    numerator: int, denominator: int
) -> None:
    value = Fraction(numerator, denominator)
    result = _evaluate(value, -value)
    assert result.passed and result.holdout_sharpe == float(value)


@given(st.integers(325, 450), st.booleans())
def test_gate_exact_positive_underflow_property_refuses_incoherent_verdict(
    exponent: int, enabled: bool
) -> None:
    value = Fraction(1, 10**exponent)
    assert value > 0 and float(value) == 0.0
    with pytest.raises(ValueError, match="projection"):
        _evaluate(value, enabled=enabled)


@given(st.integers(1, 100), st.integers(20, 100))
def test_gate_exact_benchmark_collapse_property_refuses_changed_comparison(
    base: int, exponent: int
) -> None:
    benchmark = Fraction(base)
    value = benchmark + Fraction(1, 10**exponent)
    assert value > benchmark and float(value) == float(benchmark)
    with pytest.raises(ValueError, match="projection"):
        _evaluate(value, benchmark)
