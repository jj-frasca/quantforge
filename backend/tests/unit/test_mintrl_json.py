"""ADR-386: intentional infinite required history survives strict JSON evidence."""

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st
from pydantic import BaseModel, ValidationError

from app.api.v1.lab import get_calibration_path, router
from app.research.lab.calibration import (
    CalibrationSymbolVerdict,
    NullCalibration,
    NullSymbolDiagnostics,
    PowerCalibration,
    calibrate_gate,
    collect_power_sweep,
)
from app.research.lab.experiment import (
    Experiment,
    JsonFileExperimentStore,
    PartitionedExperimentStore,
    Trial,
)
from app.research.lab.gate import GateConfig, GateResult


def _artifacts(requirement: float = math.inf) -> dict[str, BaseModel]:
    config = GateConfig()
    gate = GateResult(
        passed=False,
        dsr_ok=False,
        pbo_ok=False,
        stability_ok=True,
        mintrl_ok=False,
        holdout_ok=False,
        beats_buy_and_hold_ok=False,
        required_track_record_years=requirement,
        gate_config_version=config.version_hash,
        holdout_sharpe=0.0,
        holdout_n_bars=252,
    )
    experiment = Experiment(
        experiment_id=UUID(int=1),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        symbol="SYN",
        strategy_names=["sma"],
        gate_config=config,
        trials=[
            Trial(
                strategy_name="sma",
                parameters={"fast": 5, "slow": 20},
                observed_sharpe=0.0,
                deflated_sharpe=-1.0,
                pbo=1.0,
                parameter_stability_score=1.0,
            )
        ],
        lifetime_trials=1,
        best_strategy_name="sma",
        selected_trial_index=0,
        best_gate_result=gate,
        n_bars=1260,
    )
    verdict = CalibrationSymbolVerdict(
        symbol="SYN",
        deflated_sharpe_probability=None,
        gate_result=gate,
        holdout_sharpe=0.0,
        holdout_n_bars=252,
    )
    null = NullCalibration(
        n_symbols=1,
        n_graduates=0,
        false_graduation_rate=0.0,
        n_clear_deflation_bar=0,
        deflation_bar=0.0,
        max_deflated_sharpe=-1.0,
        max_holdout_sharpe=None,
        graduates=[],
        holdout_years=[1.0],
        n_bars=[1260],
        symbol_diagnostics=[
            NullSymbolDiagnostics(
                symbol="SYN", n_bars=1260, holdout_years=1.0, calibration_verdict=verdict
            )
        ],
        errors={},
        gate_config_version=config.version_hash,
    )
    power = PowerCalibration(
        n_symbols=1,
        n_detected=0,
        detection_rate=0.0,
        n_clear_deflation_bar=0,
        deflation_bar=0.0,
        phi=0.3,
        oracle_sharpes=[],
        holdout_years=[1.0],
        n_bars=[1260],
        symbol_verdicts=[verdict],
        finalist_deflated_sharpe_probabilities=[None],
        errors={},
        gate_config_version=config.version_hash,
    )
    return {
        "gate": gate,
        "experiment": experiment,
        "null": null,
        "power": power,
        "sweep": collect_power_sweep([power]),
    }


def _requirements(value: object) -> list[object]:
    if isinstance(value, dict):
        found = (
            [value["required_track_record_years"]] if "required_track_record_years" in value else []
        )
        return found + [leaf for child in value.values() for leaf in _requirements(child)]
    if isinstance(value, (list, tuple)):
        return [leaf for child in value for leaf in _requirements(child)]
    return []


@pytest.mark.parametrize("kind", ["gate", "experiment", "null", "power", "sweep"])
@pytest.mark.parametrize("route", ["pydantic", "python_json"])
def test_mintrl_infinity_survives_nested_strict_json(kind: str, route: str) -> None:
    original = _artifacts()[kind]
    text = (
        original.model_dump_json()
        if route == "pydantic"
        else json.dumps(original.model_dump(mode="json"), allow_nan=False)
    )
    assert _requirements(json.loads(text)) == ["Infinity"]
    assert type(original).model_validate_json(text) == original


@pytest.mark.parametrize("kind", ["gate", "experiment", "null", "power", "sweep"])
def test_mintrl_native_python_mode_remains_numeric(kind: str) -> None:
    model = _artifacts()[kind]
    assert _requirements(model.model_dump()) == [math.inf]
    assert _requirements(model.model_dump(round_trip=True)) == [math.inf]


@given(st.floats(min_value=0.0, allow_nan=False, allow_infinity=False))
def test_mintrl_finite_required_history_round_trips_as_number(value: float) -> None:
    gate = _artifacts(value)["gate"]
    assert json.loads(gate.model_dump_json())["required_track_record_years"] == value
    assert GateResult.model_validate_json(gate.model_dump_json()) == gate


@pytest.mark.parametrize("value", [None, -1.0, -math.inf, math.nan])
def test_mintrl_invalid_requirements_still_refuse(value: object) -> None:
    raw = _artifacts()["gate"].model_dump()
    raw["required_track_record_years"] = value
    with pytest.raises(ValidationError):
        GateResult.model_validate(raw)


@pytest.mark.parametrize("partitioned", [False, True])
def test_mintrl_both_pool_writers_emit_strict_reloadable_json(
    tmp_path: Path, partitioned: bool
) -> None:
    experiment = _artifacts()["experiment"]
    store = (
        PartitionedExperimentStore(tmp_path / "pool")
        if partitioned
        else JsonFileExperimentStore(tmp_path / "pool.json")
    )
    store.add(experiment)

    def refuse_nonstandard(token: str) -> object:
        raise ValueError(f"nonstandard JSON constant: {token}")

    files = list(tmp_path.rglob("*.json"))
    assert len(files) == 1
    assert _requirements(json.loads(files[0].read_text(), parse_constant=refuse_nonstandard)) == [
        "Infinity"
    ]
    assert store.all() == [experiment]


def test_mintrl_actual_null_api_retains_tag_and_declares_serialization_schema(
    tmp_path: Path,
) -> None:
    # Existing readers already accept the tag; no decoder change is needed.
    payload = _artifacts()["null"].model_dump(mode="json")
    payload["symbol_diagnostics"][0]["calibration_verdict"]["gate_result"][
        "required_track_record_years"
    ] = "Infinity"
    (tmp_path / "control.json").write_text(json.dumps(payload, allow_nan=False))
    api = FastAPI()
    api.include_router(router, prefix="/api/v1")
    api.dependency_overrides[get_calibration_path] = lambda: tmp_path
    response = TestClient(api).get("/api/v1/null-calibration")
    assert response.status_code == 200
    assert _requirements(response.json()) == ["Infinity"]
    schema = api.openapi()["components"]["schemas"]["GateResult"]["properties"][
        "required_track_record_years"
    ]
    assert {"const": "Infinity", "type": "string"} in schema["anyOf"]
    assert any(part.get("type") == "number" for part in schema["anyOf"])


def test_mintrl_official_flat_calibration_json_is_reloadable() -> None:
    frame = pd.DataFrame(
        {"open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 1e6},
        index=pd.bdate_range("2000-01-03", periods=3000, tz="UTC"),
    )
    result = calibrate_gate(
        {"SYN_FLAT": frame}, ["sma"], refine=True, null_mode="unit_mechanics_control"
    )
    assert result.n_symbols == 1 and result.n_graduates == 0
    assert _requirements(result.model_dump()) == [math.inf]
    assert _requirements(json.loads(result.model_dump_json())) == ["Infinity"]
    assert NullCalibration.model_validate_json(result.model_dump_json()) == result
