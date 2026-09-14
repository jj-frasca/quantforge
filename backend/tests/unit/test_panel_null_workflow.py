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


def test_panel_null_workflow_bounds_serial_searches_per_job() -> None:
    workflow = _workflow()
    prepare = workflow.split("  prepare:\n", 1)[1].split("\n  batch:\n", 1)[0]
    batch = workflow.split("  batch:\n", 1)[1].split("\n  consolidate:\n", 1)[0]

    assert 'PANELS_PER_SHARD: "4"' in workflow
    assert "timeout-minutes: 120" in prepare
    assert "timeout-minutes: 360" in batch
    assert "shard: [" + ", ".join(str(index) for index in range(100)) + "]" in batch


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


def test_panel_null_workflow_recovers_only_a_completed_artifact_without_remeasurement() -> None:
    workflow = _workflow()

    assert "recovery_run_id:" in workflow
    assert "recovery_run_attempt:" in workflow
    assert "actions: read" in workflow
    assert "  recover:\n" in workflow
    recover = workflow.split("  recover:\n", 1)[1]
    assert (
        "panel-null-measurement-${{ inputs.recovery_run_id }}-"
        "${{ inputs.recovery_run_attempt }}" in recover
    )
    assert "run-id: ${{ inputs.recovery_run_id }}" in recover
    assert (
        '"repos/$GITHUB_REPOSITORY/actions/runs/$RECOVERY_RUN_ID/'
        'attempts/$RECOVERY_RUN_ATTEMPT"' in recover
    )
    assert '"$RUNNER_TEMP/recovery-run.json"' in recover
    assert '"$GITHUB_REPOSITORY"' in recover
    assert '"${{ inputs.recovery_run_attempt }}"' in recover
    assert "scripts/recover_panel_null.py" in recover
    assert "scripts/prepare_panel_null.py" not in recover
    assert "scripts/run_panel_null_batch.py" not in recover
    assert "scripts/consolidate_panel_null.py" not in recover
    assert "if: inputs.recovery_run_id == ''" in workflow
    assert "if: inputs.recovery_run_id != ''" in recover


def test_panel_null_workflow_names_the_measurement_for_its_exact_run_attempt() -> None:
    workflow = _workflow()
    consolidate = workflow.split("  consolidate:\n", 1)[1].split("\n  recover:\n", 1)[0]

    assert "panel-null-measurement-${{ github.run_id }}-${{ github.run_attempt }}" in consolidate


def test_panel_null_workflow_rejects_partial_recovery_identity_before_other_jobs() -> None:
    workflow = _workflow()
    validation = workflow.split("  validate-inputs:\n", 1)[1].split("\n  prepare:\n", 1)[0]
    prepare = workflow.split("  prepare:\n", 1)[1].split("\n  batch:\n", 1)[0]
    recover = workflow.split("  recover:\n", 1)[1]

    assert '[[ -n "$RECOVERY_RUN_ID" && -z "$RECOVERY_RUN_ATTEMPT" ]]' in validation
    assert '[[ -z "$RECOVERY_RUN_ID" && -n "$RECOVERY_RUN_ATTEMPT" ]]' in validation
    assert "needs: validate-inputs" in prepare
    assert "needs: validate-inputs" in recover
