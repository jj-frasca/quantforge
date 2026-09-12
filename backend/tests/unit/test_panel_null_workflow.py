"""Static safety contract for ADR-081's expensive manual-only workflow."""

import re
from pathlib import Path

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "panel-null-calibration.yml"
)


def _workflow() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_panel_null_workflow_is_manual_only() -> None:
    trigger = _workflow().split("on:\n", 1)[1].split("\npermissions:", 1)[0]

    assert "workflow_dispatch:" in trigger
    assert "schedule:" not in trigger
    assert "push:" not in trigger
    assert "pull_request:" not in trigger


def test_panel_null_workflow_partitions_exactly_the_frozen_global_index_set() -> None:
    workflow = _workflow()
    width_match = re.search(r'^  PANELS_PER_SHARD: "(\d+)"$', workflow, re.MULTILINE)
    shards_match = re.search(r"shard: \[([\d, ]+)\]", workflow)
    assert width_match is not None
    assert shards_match is not None
    width = int(width_match.group(1))
    shards = [int(value.strip()) for value in shards_match.group(1).split(",")]
    indices = [index for shard in shards for index in range(shard * width, (shard + 1) * width)]

    assert indices == list(range(400))
    assert "START=$(( ${{ matrix.shard }} * PANELS_PER_SHARD ))" in workflow
    assert "STOP=$(( START + PANELS_PER_SHARD ))" in workflow
    assert '--range "$START" "$STOP"' in workflow


def test_panel_null_workflow_shares_one_frozen_input_pair_and_only_consolidation_writes_data() -> (
    None
):
    workflow = _workflow()
    prepare = workflow.split("  prepare:\n", 1)[1].split("\n  batch:\n", 1)[0]
    batch = workflow.split("  batch:\n", 1)[1].split("\n  consolidate:\n", 1)[0]
    consolidate = workflow.split("  consolidate:\n", 1)[1]

    assert "scripts/prepare_panel_null.py" in prepare
    assert '--code-revision "$GITHUB_SHA"' in prepare
    assert "panel-source.npz" in prepare
    assert "panel-cohort.json" in prepare
    assert "actions/upload-artifact@v4" in prepare
    assert "needs: prepare" in batch
    assert "actions/download-artifact@v4" in batch
    assert "scripts/run_panel_null_batch.py" in batch
    assert '--code-revision "$GITHUB_SHA"' in batch
    assert "panel-source.npz" in batch
    assert "panel-cohort.json" in batch
    assert "data/panel_null_calibration" not in prepare
    assert "data/panel_null_calibration" not in batch
    assert "needs: batch" in consolidate
    assert "scripts/consolidate_panel_null.py" in consolidate
    assert "data/panel_null_calibration/replicated_correlated_panel_null.json" in consolidate
    assert (
        "git add data/panel_null_calibration/replicated_correlated_panel_null.json" in consolidate
    )
