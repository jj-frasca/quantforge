"""Sole-writer consolidation boundary for ADR-081 panel-null shards."""

import sys
from datetime import date
from pathlib import Path

import pytest
from scripts.consolidate_panel_null import main

from app.research.lab.panel_null import (
    PanelNullCalibration,
    PanelNullCohort,
    PanelNullReplicate,
    PanelNullShard,
    PanelSymbolExcess,
    panel_seed,
)


def _cohort() -> PanelNullCohort:
    return PanelNullCohort(
        symbols=("AAA", "BBB"),
        symbol_excesses=(
            PanelSymbolExcess(symbol="AAA", walk_forward=-0.2, purged_cv=0.1),
            PanelSymbolExcess(symbol="BBB", walk_forward=0.0, purged_cv=0.2),
        ),
        source_start=date(1995, 1, 3),
        source_end=date(2026, 8, 31),
        source_sha256="a" * 64,
        target_n_bars=7400,
        history_tolerance=0.10,
        search_config_version="search-v1",
        gate_config_version="gate-v1",
        generator_version="joint-iid-calendar-v1",
        diagnostic_version="equal-symbol-excess-v1",
        base_seed=17,
        n_replicates=2,
        min_successful_symbols=2,
    )


def _replicate(index: int, value: float) -> PanelNullReplicate:
    return PanelNullReplicate(
        panel_index=index,
        panel_id=f"panel-{index}",
        seed=panel_seed(17, index),
        successful_symbols=2,
        walk_forward_excess=value,
        purged_cv_excess=value + 0.1,
    )


def test_consolidator_writes_one_validated_complete_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    shard_dir = tmp_path / "shards"
    shard_dir.mkdir()
    cohort = _cohort()
    (shard_dir / "later.json").write_text(
        PanelNullShard(cohort=cohort, replicates=(_replicate(1, 0.2),)).model_dump_json()
    )
    (shard_dir / "earlier.json").write_text(
        PanelNullShard(cohort=cohort, replicates=(_replicate(0, -0.3),)).model_dump_json()
    )
    output = tmp_path / "panel-null.json"
    monkeypatch.setattr(sys, "argv", ["consolidate_panel_null.py", str(shard_dir), str(output)])

    main()

    result = PanelNullCalibration.model_validate_json(output.read_text())
    assert tuple(replicate.panel_index for replicate in result.replicates) == (0, 1)
    assert result.cohort == cohort
    rendered = capsys.readouterr().out
    assert "whole-panel replicates: 2" in rendered
    assert "walk-forward excess" in rendered
    assert "wrote" in rendered
