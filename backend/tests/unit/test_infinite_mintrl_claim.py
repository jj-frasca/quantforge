"""ADR-387: finite available history cannot satisfy an infinite requirement."""

import json
import math
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError
from tests.unit.test_gate_result_identity import _result
from tests.unit.test_mintrl_json import _artifacts

from app.research.lab.calibration import CalibrationSymbolVerdict
from app.research.lab.experiment import (
    Graduate,
    JsonFileExperimentStore,
    PartitionedExperimentStore,
)
from app.research.lab.gate import GateResult

ERROR = "infinite required_track_record_years requires mintrl_ok=False"


@pytest.mark.parametrize("route", ["constructor", "mapping", "json", "instance"])
@pytest.mark.parametrize("dsr_ok", [False, True])
@pytest.mark.parametrize("legacy_holdout", [False, True])
def test_infinite_mintrl_refuses_passing_leg(
    route: str, dsr_ok: bool, legacy_holdout: bool
) -> None:
    raw = _result().model_dump(round_trip=True)
    raw.update(required_track_record_years=math.inf, dsr_ok=dsr_ok, passed=dsr_ok)
    if legacy_holdout:
        raw.update(holdout_sharpe=None, holdout_n_bars=None)
    with pytest.raises(ValidationError, match=ERROR):
        if route == "constructor":
            GateResult(**raw)
        elif route == "mapping":
            GateResult.model_validate(raw)
        elif route == "json":
            raw["required_track_record_years"] = "Infinity"
            GateResult.model_validate_json(json.dumps(raw, allow_nan=False))
        else:
            GateResult.model_validate(_result().model_copy(update=raw))


@pytest.mark.parametrize("kind", ["experiment", "null", "power", "sweep"])
@pytest.mark.parametrize("route", ["mapping", "json"])
def test_infinite_mintrl_outer_claims_refuse_contradictory_leg(kind: str, route: str) -> None:
    model = _artifacts()[kind]
    raw = model.model_dump(mode="json")

    def corrupt(value: object) -> None:
        if isinstance(value, dict):
            if "required_track_record_years" in value:
                value["mintrl_ok"] = True
            for child in value.values():
                corrupt(child)
        elif isinstance(value, list):
            for child in value:
                corrupt(child)

    corrupt(raw)
    with pytest.raises(ValidationError, match=ERROR):
        if route == "mapping":
            type(model).model_validate(raw)
        else:
            type(model).model_validate_json(json.dumps(raw, allow_nan=False))


@pytest.mark.parametrize("consumer", ["verdict", "graduate"])
def test_infinite_mintrl_nested_instances_refuse_contradiction(consumer: str) -> None:
    bad = _result().model_copy(update={"required_track_record_years": math.inf})
    with pytest.raises(ValidationError, match=ERROR):
        if consumer == "verdict":
            CalibrationSymbolVerdict(
                symbol="SYN",
                deflated_sharpe_probability=0.99,
                gate_result=bad,
                holdout_sharpe=1.0,
                holdout_n_bars=252,
            )
        else:
            Graduate(
                strategy_name="sma",
                parameters={"fast": 5, "slow": 20},
                gate_result=bad,
                holdout_sharpe=1.0,
                holdout_n_bars=252,
                holdout_total_return=0.1,
            )


@pytest.mark.parametrize("partitioned", [False, True])
def test_infinite_mintrl_stores_refuse_unchecked_claim_before_output(
    tmp_path: Path, partitioned: bool
) -> None:
    model = _artifacts()["experiment"]
    bad_gate = model.best_gate_result.model_copy(update={"mintrl_ok": True})
    bad = model.model_copy(update={"best_gate_result": bad_gate})
    target = tmp_path / ("pool" if partitioned else "pool.json")
    store = PartitionedExperimentStore(target) if partitioned else JsonFileExperimentStore(target)
    with pytest.raises(ValidationError, match=ERROR):
        store.add(bad)
    assert not target.exists()


@given(
    required=st.floats(min_value=0.0, allow_nan=False, allow_infinity=False),
    mintrl_ok=st.booleans(),
)
def test_infinite_mintrl_preserves_every_finite_requirement(
    required: float, mintrl_ok: bool
) -> None:
    gate = _result(required_track_record_years=required, mintrl_ok=mintrl_ok, passed=mintrl_ok)
    assert gate.required_track_record_years == required
    assert gate.mintrl_ok is mintrl_ok
    assert GateResult.model_validate_json(gate.model_dump_json()) == gate


@given(dsr_ok=st.booleans(), pbo_ok=st.booleans(), holdout_ok=st.booleans())
def test_infinite_mintrl_validated_infinite_requirement_always_rejects_leg(
    dsr_ok: bool, pbo_ok: bool, holdout_ok: bool
) -> None:
    fields = {
        "required_track_record_years": math.inf,
        "dsr_ok": dsr_ok,
        "pbo_ok": pbo_ok,
        "holdout_ok": holdout_ok,
    }
    valid = _result(**fields, mintrl_ok=False, passed=False)
    assert valid.mintrl_ok is False
    assert json.loads(valid.model_dump_json())["required_track_record_years"] == "Infinity"
    assert GateResult.model_validate_json(valid.model_dump_json()) == valid
    with pytest.raises(ValidationError, match=ERROR):
        _result(**fields, mintrl_ok=True, passed=dsr_ok and pbo_ok and holdout_ok)


def test_infinite_mintrl_preserves_existing_conjunction_error_precedence() -> None:
    with pytest.raises(ValidationError, match="passed must equal the conjunction"):
        _result(required_track_record_years=math.inf, passed=False)
