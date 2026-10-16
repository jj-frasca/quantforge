"""ADR-294: historical numbers remain intact while procedure attribution is explicit."""

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.v1.lab import get_calibration_path, get_power_calibration_path
from app.main import app
from app.research.lab.calibration import NullCalibration, PowerSweep, calibration_search_version
from app.research.lab.gate import GateConfig
from app.research.lab.history import CALIBRATION_N_BARS
from app.research.strategies.catalog import STRATEGY_CATALOG


def reference() -> dict[str, Any]:
    config = GateConfig()
    names = sorted(entry.name for entry in STRATEGY_CATALOG)
    return {
        "search_config_version": calibration_search_version(
            names,
            n_per_param=3,
            config=config,
            refine=True,
            refine_span=0.25,
            select_by="observed",
        ),
        "gate_config_version": config.version_hash,
        "n_bars": CALIBRATION_N_BARS,
        "strategy_names": names,
        "n_per_param": 3,
        "refine": True,
        "refine_span": 0.25,
        "select_by": "observed",
    }


def null_payload() -> dict[str, Any]:
    ref = reference()
    return {
        "n_symbols": 2,
        "n_graduates": 0,
        "false_graduation_rate": 0.0,
        "n_clear_deflation_bar": 0,
        "deflation_bar": 1.5,
        "max_deflated_sharpe": -0.1,
        "max_holdout_sharpe": None,
        "graduates": [],
        "holdout_years": [5.0],
        "errors": {},
        "n_bars": [ref["n_bars"]] * 2,
        "gate_config_version": ref["gate_config_version"],
        "search_config_version": ref["search_config_version"],
        "refine": True,
        "refine_span": 0.25,
        "null_mode": "iid_normal",
    }


def sweep_payload() -> dict[str, Any]:
    ref = reference()
    cell = {
        "n_symbols": 2,
        "n_detected": 0,
        "detection_rate": 0.0,
        "n_clear_deflation_bar": 0,
        "deflation_bar": 1.5,
        "edge": "ar1",
        "phi": 0.3,
        "oracle_sharpes": [],
        "holdout_years": [5.0],
        "errors": {},
        "n_bars": [ref["n_bars"]] * 2,
        "gate_config_version": ref["gate_config_version"],
        "search_config_version": ref["search_config_version"],
        "refine": True,
        "refine_span": 0.25,
    }
    return {
        "edge": "ar1",
        "gate_config_version": ref["gate_config_version"],
        "search_config_version": ref["search_config_version"],
        "n_bars": ref["n_bars"],
        "cells": [cell],
    }


def request_rows(tmp_path: Path, kind: str, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for i, payload in enumerate(payloads):
        (tmp_path / f"{i:02d}.json").write_text(json.dumps(payload))
    dependency = get_calibration_path if kind == "null" else get_power_calibration_path
    endpoint = "null-calibration" if kind == "null" else "power-calibration"
    app.dependency_overrides[dependency] = lambda: tmp_path
    try:
        response = TestClient(app).get(f"/api/v1/{endpoint}")
        assert response.status_code == 200
        return response.json()  # type: ignore[no-any-return]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("kind", ["null", "power"])
def test_calibration_matched_procedure_and_history_returns_explicit_context(
    tmp_path: Path,
    kind: str,
) -> None:
    payload = null_payload() if kind == "null" else sweep_payload()
    context = request_rows(tmp_path, kind, [payload])[0]["compatibility"]
    assert {context[k] for k in ["status", "search", "gate", "history"]} == {"MATCHED"}
    assert context["reference"] == reference()
    assert context["reasons"] == []


@pytest.mark.parametrize(
    "change,expected",
    [
        ({"search_config_version": "0" * 64}, ("DIFFERENT", "MATCHED", "MATCHED")),
        ({"gate_config_version": "0" * 64}, ("MATCHED", "DIFFERENT", "MATCHED")),
        ({"n_bars": [5400, 5400]}, ("MATCHED", "MATCHED", "DIFFERENT")),
        ({"n_bars": [7400, 5400]}, ("MATCHED", "MATCHED", "DIFFERENT")),
        ({"n_bars": [5400]}, ("MATCHED", "MATCHED", "DIFFERENT")),
        ({"n_bars": [7400]}, ("MATCHED", "MATCHED", "UNKNOWN")),
        ({"n_bars": []}, ("MATCHED", "MATCHED", "UNKNOWN")),
        ({"search_config_version": "legacy-unspecified"}, ("UNKNOWN", "MATCHED", "MATCHED")),
        ({"search_config_version": "bad-hash"}, ("UNKNOWN", "MATCHED", "MATCHED")),
        ({"search_config_version": ""}, ("UNKNOWN", "MATCHED", "MATCHED")),
        ({"search_config_version": "0" * 64, "n_bars": []}, ("DIFFERENT", "MATCHED", "UNKNOWN")),
    ],
)
def test_null_calibration_dimension_evidence_qualifies_context(
    tmp_path: Path,
    change: dict[str, Any],
    expected: tuple[str, str, str],
) -> None:
    context = request_rows(tmp_path, "null", [null_payload() | change])[0]["compatibility"]
    assert tuple(context[k] for k in ["search", "gate", "history"]) == expected
    assert context["status"] == ("DIFFERENT" if "DIFFERENT" in expected else "UNKNOWN")
    assert context["reasons"]


@pytest.mark.parametrize("field", ["search_config_version", "n_bars"])
def test_null_calibration_missing_raw_lineage_stays_unknown(
    tmp_path: Path,
    field: str,
) -> None:
    payload = null_payload()
    del payload[field]
    context = request_rows(tmp_path, "null", [payload])[0]["compatibility"]
    assert context["status"] == "UNKNOWN"
    assert context["search" if field == "search_config_version" else "history"] == "UNKNOWN"


@pytest.mark.parametrize(
    "location,field,value,dimension,state",
    [
        ("header", "search_config_version", "0" * 64, "search", "DIFFERENT"),
        ("cell", "search_config_version", "0" * 64, "search", "DIFFERENT"),
        ("cell", "gate_config_version", "0" * 64, "gate", "DIFFERENT"),
        ("cell", "search_config_version", "legacy-unspecified", "search", "UNKNOWN"),
        ("cell", "n_bars", [7400], "history", "UNKNOWN"),
        ("cell", "n_bars", [], "history", "UNKNOWN"),
        ("cell", "n_bars", [5400], "history", "DIFFERENT"),
        ("cell", "n_bars", [7400, 5400], "history", "DIFFERENT"),
        ("header", "n_bars", 5400, "history", "DIFFERENT"),
        ("header", "n_bars", "7400", "history", "UNKNOWN"),
        ("header", "n_bars", True, "history", "UNKNOWN"),
    ],
)
def test_power_calibration_header_and_every_cell_qualify_context(
    tmp_path: Path,
    location: str,
    field: str,
    value: Any,
    dimension: str,
    state: str,
) -> None:
    payload = sweep_payload()
    payload["cells"].append(dict(payload["cells"][0]))
    target = payload if location == "header" else payload["cells"][1]
    target[field] = value
    context = request_rows(tmp_path, "power", [payload])[0]["compatibility"]
    assert context["status"] == context[dimension] == state
    assert context["reasons"]


def test_power_calibration_known_cell_difference_outranks_missing_cell_lineage(
    tmp_path: Path,
) -> None:
    payload = sweep_payload()
    payload["cells"].append(dict(payload["cells"][0]))
    del payload["cells"][0]["search_config_version"]
    payload["cells"][1]["search_config_version"] = "0" * 64
    context = request_rows(tmp_path, "power", [payload])[0]["compatibility"]
    assert context["search"] == context["status"] == "DIFFERENT"
    assert any("unavailable" in reason for reason in context["reasons"])
    assert any("differs" in reason for reason in context["reasons"])


def test_power_calibration_empty_cells_cannot_match_default(tmp_path: Path) -> None:
    payload = sweep_payload() | {"cells": []}
    context = request_rows(tmp_path, "power", [payload])[0]["compatibility"]
    assert (
        context["status"] == context["search"] == context["gate"] == context["history"] == "UNKNOWN"
    )


def test_null_calibration_custom_selector_is_different_not_invalid(tmp_path: Path) -> None:
    payload = null_payload()
    payload["search_config_version"] = calibration_search_version(
        reference()["strategy_names"],
        n_per_param=3,
        config=GateConfig(),
        select_by="walk_forward",
    )
    row = request_rows(tmp_path, "null", [payload])[0]
    assert row["compatibility"]["search"] == "DIFFERENT"
    assert row["false_graduation_rate"] == payload["false_graduation_rate"]


@pytest.mark.parametrize("kind", ["null", "power"])
def test_calibration_reference_failure_preserves_historical_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    from app.api import calibration_compatibility as compatibility_module

    def unavailable() -> None:
        raise RuntimeError("reference unavailable")

    monkeypatch.setattr(compatibility_module, "current_calibration_reference", unavailable)
    payload = null_payload() if kind == "null" else sweep_payload()
    row = request_rows(tmp_path, kind, [payload])[0]
    context = row.pop("compatibility")
    expected = (
        NullCalibration.model_validate(payload)
        if kind == "null"
        else PowerSweep.model_validate(payload)
    )
    assert row == expected.model_dump(mode="json")
    assert context["reference"] is None
    assert {context[k] for k in ["status", "search", "gate", "history"]} == {"UNKNOWN"}


@pytest.mark.parametrize("kind", ["null", "power"])
def test_calibration_reference_failure_does_not_swallow_scientific_parse_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    from app.api import calibration_compatibility as compatibility_module

    def unavailable() -> None:
        raise RuntimeError("reference unavailable")

    monkeypatch.setattr(compatibility_module, "current_calibration_reference", unavailable)
    payload = null_payload() if kind == "null" else sweep_payload()
    target = payload if kind == "null" else payload["cells"][0]
    target["n_symbols"] = 0
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        request_rows(tmp_path, kind, [payload])


@pytest.mark.parametrize("kind", ["null", "power"])
def test_calibration_values_order_files_and_single_request_reference_remain_intact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    from app.api import calibration_compatibility as compatibility_module

    calls = []
    original = compatibility_module.current_calibration_reference

    def counted() -> Any:
        calls.append(1)
        return original()

    monkeypatch.setattr(compatibility_module, "current_calibration_reference", counted)
    first = null_payload() if kind == "null" else sweep_payload()
    second = null_payload() if kind == "null" else sweep_payload()
    second["null_mode" if kind == "null" else "edge"] = "second"
    model = NullCalibration if kind == "null" else PowerSweep
    expected = [model.model_validate(p).model_dump(mode="json") for p in [first, second]]
    rows = request_rows(tmp_path, kind, [first, second])
    assert len(calls) == 1
    assert [row.pop("compatibility") for row in rows]
    assert rows == expected
    assert [(tmp_path / f"{i:02d}.json").read_text() for i in range(2)] == [
        json.dumps(p) for p in [first, second]
    ]


@pytest.mark.parametrize("kind", ["null", "power"])
def test_calibration_nonobject_artifact_preserves_authoritative_validation_error(
    tmp_path: Path,
    kind: str,
) -> None:
    from pydantic import ValidationError

    # Previously model_validate_json rejected this as a scientific model error.
    with pytest.raises(ValidationError):
        request_rows(tmp_path, kind, [[]])  # type: ignore[list-item]


@pytest.mark.parametrize("kind", ["null", "power"])
def test_calibration_invalid_json_preserves_authoritative_validation_error(
    tmp_path: Path,
    kind: str,
) -> None:
    from pydantic import ValidationError

    (tmp_path / "invalid.json").write_text("{")
    with pytest.raises(ValidationError):
        request_rows(tmp_path, kind, [])
