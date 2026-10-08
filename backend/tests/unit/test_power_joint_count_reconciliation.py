"""Complete joint verdicts bind modern power headline and component counts."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.research.lab.calibration import (
    CalibrationSymbolVerdict,
    PowerCalibration,
    collect_power_sweep,
)
from app.research.lab.gate import GateResult

COMPONENTS = ["dsr", "pbo", "stability", "mintrl", "holdout", "beats_buy_and_hold"]


def verdict(
    symbol: str,
    *,
    score: float = 0.0,
    bars: int = 252,
    passed: bool = True,
    probability: float | None = 0.99,
) -> CalibrationSymbolVerdict:
    return CalibrationSymbolVerdict(
        symbol=symbol,
        deflated_sharpe_probability=probability,
        holdout_sharpe=score,
        holdout_n_bars=bars,
        gate_result=GateResult(
            passed=passed,
            dsr_ok=passed,
            pbo_ok=True,
            stability_ok=True,
            mintrl_ok=True,
            holdout_ok=True,
            beats_buy_and_hold_ok=True,
            required_track_record_years=1.0,
            gate_config_version="gate",
            holdout_sharpe=score,
            holdout_n_bars=bars,
        ),
    )


def payload(
    records: list[CalibrationSymbolVerdict],
    *,
    detected: int = 2,
    survivors: int = 0,
    counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    return {
        "n_symbols": len(records),
        "n_detected": detected,
        "detection_rate": detected / len(records),
        "n_clear_deflation_bar": survivors,
        "deflation_bar": 0.0,
        "phi": 0.3,
        "oracle_sharpes": [],
        "holdout_years": [v.holdout_n_bars / 252 for v in records],
        "n_bars": [1260] * len(records),
        "errors": {},
        "gate_config_version": "gate",
        "symbol_verdicts": records,
        "finalist_deflated_sharpe_probabilities": [v.deflated_sharpe_probability for v in records],
        "gate_pass_counts": {} if counts is None else counts,
    }


def pair() -> list[CalibrationSymbolVerdict]:
    return [verdict("A"), verdict("B")]


@pytest.mark.parametrize("detected", [0, 1])
def test_headline_detection_cannot_disagree_with_complete_joint_evidence(detected: int) -> None:
    with pytest.raises(ValidationError, match="n_detected"):
        PowerCalibration.model_validate(payload(pair(), detected=detected))


@pytest.mark.parametrize("survivors", [1, 2])
def test_headline_survival_cannot_disagree_with_complete_joint_evidence(survivors: int) -> None:
    with pytest.raises(ValidationError, match="n_clear_deflation_bar"):
        PowerCalibration.model_validate(payload(pair(), survivors=survivors))


@pytest.mark.parametrize("component", COMPONENTS)
@pytest.mark.parametrize("count", [0, 1])
def test_present_component_count_must_match_complete_joint_evidence(
    component: str, count: int
) -> None:
    with pytest.raises(ValidationError, match="gate_pass_counts"):
        PowerCalibration.model_validate(payload(pair(), counts={component: count}))


@pytest.mark.parametrize("score,survivors", [(-1.0, 0), (0.0, 0), (1.0, 1)])
def test_survival_retains_strict_own_record_bar(score: float, survivors: int) -> None:
    root = PowerCalibration.model_validate(
        payload([verdict("A", score=score)], detected=1, survivors=survivors)
    )
    assert root.n_clear_deflation_bar == survivors


def test_survival_uses_each_records_history_and_only_incumbent_passers() -> None:
    records = [verdict("short", score=1.0), verdict("long", score=1.0, bars=1008)]
    root = PowerCalibration.model_validate(payload(records, survivors=1))
    assert root.n_clear_deflation_bar == 1
    failed = [verdict("A", score=10.0, passed=False), verdict("B", score=10.0)]
    root = PowerCalibration.model_validate(payload(failed, detected=1, survivors=1))
    assert root.n_clear_deflation_bar == 1


@pytest.mark.parametrize(
    "counts", [{}, {"dsr": 2}, {"dsr": 2, "legacy-name": 1}, dict.fromkeys(COMPONENTS, 2)]
)
def test_empty_partial_and_existing_unknown_key_semantics_remain(counts: dict[str, int]) -> None:
    root = PowerCalibration.model_validate(payload(pair(), counts=counts))
    assert root.gate_pass_counts == counts
    assert PowerCalibration.model_validate_json(root.model_dump_json()) == root


def test_nullable_candidate_does_not_remove_incumbent_evidence() -> None:
    records = [verdict("A", probability=None), verdict("B", probability=None)]
    root = PowerCalibration.model_validate(payload(records, counts={"dsr": 2}))
    assert root.n_detected == 2 and root.finalist_deflated_sharpe_probabilities == [None, None]
    assert collect_power_sweep([root]).cells[0] == root


@pytest.mark.parametrize(
    "changes",
    [
        {"n_detected": 0, "detection_rate": 0.0},
        {"n_clear_deflation_bar": 1},
        {"gate_pass_counts": {"pbo": 1}},
    ],
)
def test_sweep_rejects_unchecked_joint_headline_or_count(changes: dict[str, Any]) -> None:
    root = PowerCalibration.model_validate(payload(pair()))
    with pytest.raises(ValidationError):
        collect_power_sweep([root.model_copy(update=changes)])


def test_legacy_absent_joint_records_remain_unmeasured_and_unreconciled() -> None:
    data = payload(pair(), detected=0, counts={"dsr": 1})
    data["symbol_verdicts"] = []
    data["finalist_deflated_sharpe_probabilities"] = []
    root = PowerCalibration.model_validate(data)
    assert root.n_detected == 0 and root.gate_pass_counts == {"dsr": 1}


def test_json_rejects_typed_coherent_but_joint_inconsistent_headline() -> None:
    root = PowerCalibration.model_validate(payload(pair()))
    raw = root.model_copy(update={"n_detected": 0, "detection_rate": 0.0}).model_dump_json()
    with pytest.raises(ValidationError, match="n_detected"):
        PowerCalibration.model_validate_json(raw)


def test_sweep_rejects_unchecked_nested_incumbent_change() -> None:
    root = PowerCalibration.model_validate(payload(pair()))
    records = list(root.symbol_verdicts)
    bad_gate = records[0].gate_result.model_copy(update={"passed": False, "dsr_ok": False})
    records[0] = records[0].model_copy(update={"gate_result": bad_gate})
    with pytest.raises(ValidationError, match="n_detected"):
        collect_power_sweep([root.model_copy(update={"symbol_verdicts": records})])
