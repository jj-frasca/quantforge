"""ADR-160: GateResult is one immutable, internally coherent graduation claim."""

import math

import pytest
from pydantic import ValidationError

from app.research.lab.gate import GateResult


def _result(**updates: object) -> GateResult:
    payload: dict[str, object] = {
        "passed": True,
        "dsr_ok": True,
        "pbo_ok": True,
        "stability_ok": True,
        "mintrl_ok": True,
        "holdout_ok": True,
        "beats_buy_and_hold_ok": True,
        "required_track_record_years": 2.0,
        "gate_config_version": "gate-v1",
        "reasons": [],
        "holdout_sharpe": 1.0,
        "holdout_n_bars": 252,
    }
    payload.update(updates)
    return GateResult.model_validate(payload)


def test_gate_result_defensively_copies_and_freezes_reasons() -> None:
    reasons = ["measured rejection"]
    result = _result(passed=False, dsr_ok=False, reasons=reasons)
    reasons.append("caller mutation")

    assert result.reasons == ["measured rejection"]
    with pytest.raises((AttributeError, TypeError)):
        result.reasons.append("public mutation")
    assert isinstance(result.model_dump()["reasons"], list)


@pytest.mark.parametrize(
    "updates",
    [
        {"passed": False},
        {"dsr_ok": False},
        {"required_track_record_years": float("nan")},
        {"required_track_record_years": -0.1},
        {"gate_config_version": ""},
        {"holdout_sharpe": None},
        {"holdout_n_bars": None},
    ],
)
def test_gate_result_rejects_incoherent_claims(updates: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _result(**updates)


def test_gate_result_preserves_infinite_mintrl_for_non_positive_sharpe() -> None:
    result = _result(
        passed=False,
        dsr_ok=False,
        mintrl_ok=False,
        required_track_record_years=math.inf,
        reasons=["non-positive observed Sharpe"],
    )

    assert result.required_track_record_years == math.inf
