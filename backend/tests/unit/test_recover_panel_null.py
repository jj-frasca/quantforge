"""Publish-only recovery for ADR-087's already completed panel-null artifact."""

import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError
from scripts.recover_panel_null import recover_panel_null_measurement

from app.research.lab.panel_null import (
    PanelNullCalibration,
    PanelNullCohort,
    PanelNullReplicate,
    PanelSymbolExcess,
    panel_seed,
)


def _calibration() -> PanelNullCalibration:
    cohort = PanelNullCohort(
        symbols=("AAA",),
        symbol_excesses=(PanelSymbolExcess(symbol="AAA", walk_forward=-0.1),),
        source_start=date(1995, 1, 3),
        source_end=date(2026, 8, 31),
        source_sha256="a" * 64,
        target_n_bars=7400,
        history_tolerance=0.10,
        search_config_version="search-v1",
        gate_config_version="gate-v1",
        code_revision="1" * 40,
        generator_version="joint-iid-calendar-v1",
        diagnostic_version="equal-symbol-source-matched-excess-v2",
        base_seed=17,
        n_replicates=1,
        min_successful_symbols=1,
    )
    return PanelNullCalibration(
        cohort=cohort,
        replicates=(
            PanelNullReplicate(
                panel_index=0,
                panel_id="panel-000",
                seed=panel_seed(17, 0),
                successful_symbols=1,
                walk_forward_excess=0.2,
            ),
        ),
    )


def test_recovery_validates_then_preserves_the_completed_artifact_bytes(tmp_path: Path) -> None:
    source = tmp_path / "completed.json"
    output = tmp_path / "published.json"
    payload = _calibration().model_dump_json(indent=2) + "\n"
    source.write_text(payload, encoding="utf-8")

    recovered = recover_panel_null_measurement(source, output)

    assert recovered == _calibration()
    assert output.read_bytes() == source.read_bytes()


def test_recovery_rejects_invalid_payload_before_replacing_the_destination(tmp_path: Path) -> None:
    source = tmp_path / "invalid.json"
    output = tmp_path / "published.json"
    source.write_text('{"cohort": {}}\n', encoding="utf-8")
    output.write_text("previous measurement\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        recover_panel_null_measurement(source, output)

    assert output.read_text(encoding="utf-8") == "previous measurement\n"


def test_recovery_rejects_noncanonical_extra_fields_before_replacing_destination(
    tmp_path: Path,
) -> None:
    source = tmp_path / "completed.json"
    output = tmp_path / "published.json"
    payload = json.loads(_calibration().model_dump_json())
    payload["unvalidated_note"] = "must not survive recovery"
    source.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    output.write_text("previous measurement\n", encoding="utf-8")

    with pytest.raises(ValueError, match="canonical panel-null calibration"):
        recover_panel_null_measurement(source, output)

    assert output.read_text(encoding="utf-8") == "previous measurement\n"
