"""Joint calibration claims require original scalar evidence before coercion."""

import json
from fractions import Fraction
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError

from app.research.lab.calibration import (
    CalibrationSymbolVerdict,
    NullCalibration,
    NullSymbolDiagnostics,
    PowerCalibration,
    collect_power_sweep,
)
from app.research.lab.gate import GateResult
from app.research.lab.probability_dsr import compare_probability_dsr_gate


def payload(**changes: Any) -> dict[str, Any]:
    fields = {"deflated_sharpe_probability": 0.99, "holdout_sharpe": 1.0, "holdout_n_bars": 252}
    fields.update(changes)
    # Valid original incumbent evidence, with matching projections where representable.
    score = float(fields["holdout_sharpe"])
    bars = int(fields["holdout_n_bars"])
    gate = GateResult(
        passed=True,
        dsr_ok=True,
        pbo_ok=True,
        stability_ok=True,
        mintrl_ok=True,
        holdout_ok=True,
        beats_buy_and_hold_ok=True,
        required_track_record_years=1.0,
        gate_config_version="gate",
        holdout_sharpe=score if np.isfinite(score) else 1.0,
        holdout_n_bars=bars if bars > 0 else 252,
    )
    return {"symbol": "EDGE", "gate_result": gate.model_dump(), **fields}


BAD = (
    [
        ("deflated_sharpe_probability", v)
        for v in [
            True,
            False,
            "0.5",
            Fraction(10**400 + 1, 10**400),
            Fraction(-1, 10**400),
            -0.1,
            1.1,
            float("nan"),
            float("inf"),
        ]
    ]
    + [("holdout_sharpe", v) for v in [True, False, "1", float("nan"), float("inf")]]
    + [("holdout_n_bars", v) for v in [True, 252.0, "252", 0, -1, 1.5]]
)


@pytest.mark.parametrize("field,value", BAD)
def test_joint_verdict_rejects_invalid_original_scalar(field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        CalibrationSymbolVerdict.model_validate(payload(**{field: value}))


@pytest.mark.parametrize(
    "field,value",
    [
        ("deflated_sharpe_probability", True),
        ("deflated_sharpe_probability", "0.5"),
        ("holdout_sharpe", True),
        ("holdout_sharpe", "1"),
        ("holdout_n_bars", True),
        ("holdout_n_bars", 252.0),
        ("holdout_n_bars", "252"),
    ],
)
def test_joint_verdict_json_rejects_original_coercion(field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        CalibrationSymbolVerdict.model_validate_json(json.dumps(payload(**{field: value})))


@pytest.mark.parametrize(
    "probability,expected", [(None, None), (0.0, False), (0.95, False), (0.99, True), (1.0, True)]
)
def test_nullable_probability_and_strict_preregistered_rule_remain(
    probability: Any, expected: Any
) -> None:
    verdict = CalibrationSymbolVerdict.model_validate(
        payload(deflated_sharpe_probability=probability)
    )
    assert verdict.passes_preregistered_probability_gate is expected
    assert CalibrationSymbolVerdict.model_validate_json(verdict.model_dump_json()) == verdict


@pytest.mark.parametrize("score", [-2.0, 0.0, np.float32(0.5), Fraction(-1, 3)])
def test_signed_numeric_joint_evidence_remains_supported(score: Any) -> None:
    verdict = CalibrationSymbolVerdict.model_validate(
        payload(
            holdout_sharpe=score,
            holdout_n_bars=np.int64(252),
            deflated_sharpe_probability=Fraction(1, 2),
        )
    )
    assert verdict.holdout_sharpe == float(score)
    assert verdict.holdout_n_bars == 252 and verdict.deflated_sharpe_probability == 0.5


@pytest.mark.parametrize("field,value", [("holdout_sharpe", 2.0), ("holdout_n_bars", 253)])
def test_joint_holdout_projection_mismatch_still_rejected(field: str, value: Any) -> None:
    data = payload()
    data[field] = value
    with pytest.raises(ValidationError, match="does not match gate_result"):
        CalibrationSymbolVerdict.model_validate(data)


def power(verdict: CalibrationSymbolVerdict) -> PowerCalibration:
    return PowerCalibration(
        n_symbols=1,
        n_detected=1,
        detection_rate=1.0,
        n_clear_deflation_bar=1,
        deflation_bar=0.0,
        phi=0.3,
        oracle_sharpes=[],
        holdout_years=[1.0],
        n_bars=[1260],
        errors={},
        gate_config_version="gate",
        symbol_verdicts=[verdict],
        finalist_deflated_sharpe_probabilities=[verdict.deflated_sharpe_probability],
    )


def test_current_power_nullable_joint_attachment_round_trips() -> None:
    root = power(CalibrationSymbolVerdict.model_validate(payload(deflated_sharpe_probability=None)))
    assert PowerCalibration.model_validate_json(root.model_dump_json()) == root
    assert collect_power_sweep([root]).cells[0] == root


@pytest.mark.parametrize(
    "field,value",
    [("holdout_sharpe", True), ("holdout_n_bars", 252.0), ("deflated_sharpe_probability", True)],
)
def test_sweep_reconstruction_rejects_unchecked_joint_scalar(field: str, value: Any) -> None:
    original = CalibrationSymbolVerdict.model_validate(
        payload(holdout_sharpe=1.0, holdout_n_bars=252, deflated_sharpe_probability=1.0)
    )
    root = power(original)
    bad = original.model_copy(update={field: value})
    unchecked = root.model_copy(update={"symbol_verdicts": [bad]})
    with pytest.raises(ValidationError, match="calibration"):
        collect_power_sweep([unchecked])


@pytest.mark.parametrize("field,value", [("holdout_sharpe", True), ("holdout_n_bars", 252.0)])
def test_probability_comparison_rejects_unchecked_null_joint_scalar(field: str, value: Any) -> None:
    original = CalibrationSymbolVerdict.model_validate(payload())
    diagnostic = NullSymbolDiagnostics(
        symbol="EDGE",
        n_bars=1260,
        holdout_years=1.0,
        deflated_sharpe_probability=original.deflated_sharpe_probability,
        calibration_verdict=original,
    )
    root = NullCalibration(
        n_symbols=1,
        n_graduates=0,
        false_graduation_rate=0.0,
        n_clear_deflation_bar=0,
        deflation_bar=0.0,
        graduates=[],
        max_deflated_sharpe=0.0,
        max_holdout_sharpe=None,
        holdout_years=[1.0],
        n_bars=[1260],
        errors={},
        gate_config_version="gate",
        symbol_diagnostics=[diagnostic],
    )
    bad = original.model_copy(update={field: value})
    unchecked = root.model_copy(
        update={
            "symbol_diagnostics": [diagnostic.model_copy(update={"calibration_verdict": bad})],
        }
    )
    with pytest.raises(ValidationError, match="calibration"):
        compare_probability_dsr_gate([unchecked], collect_power_sweep([power(original)]))
