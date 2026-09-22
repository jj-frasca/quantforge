"""Publish one already completed panel-null artifact without remeasurement (ADR-087).

Usage: PYTHONPATH=. uv run python scripts/recover_panel_null.py \\
  SOURCE_JSON RUN_METADATA_JSON EXPECTED_REPOSITORY EXPECTED_RUN_ID EXPECTED_RUN_ATTEMPT OUT_JSON

The source must deserialize as a complete ``PanelNullCalibration``. Validation finishes before the
destination is touched, including binding its code revision to the authoritative GitHub source-run
metadata, then the exact source bytes replace the generated-data path atomically. Only the manual
panel-null workflow may invoke this against ``data/`` under ADR-030.
"""

import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import BaseModel, ConfigDict, Field

from app.research.lab.panel_null import PanelNullCalibration

_PANEL_NULL_WORKFLOW = ".github/workflows/panel-null-calibration.yml"


class _RunRepository(BaseModel):
    model_config = ConfigDict(frozen=True)

    full_name: str = Field(min_length=1)


class _WorkflowRunMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int = Field(gt=0)
    run_attempt: int = Field(gt=0)
    path: str = Field(min_length=1)
    event: str = Field(min_length=1)
    status: str = Field(min_length=1)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    repository: _RunRepository


def _validate_source_run(
    calibration: PanelNullCalibration,
    metadata: _WorkflowRunMetadata,
    *,
    expected_repository: str,
    expected_run_id: int,
    expected_run_attempt: int,
) -> None:
    if metadata.id != expected_run_id:
        raise ValueError("source workflow run ID does not match the requested recovery run")
    if metadata.run_attempt != expected_run_attempt:
        raise ValueError(
            "source workflow run attempt does not match the requested recovery attempt"
        )
    if calibration.cohort.workflow_run_id != expected_run_id:
        raise ValueError("artifact workflow run ID does not match the requested recovery run")
    if calibration.cohort.workflow_run_attempt != expected_run_attempt:
        raise ValueError(
            "artifact workflow run attempt does not match the requested recovery attempt"
        )
    if metadata.repository.full_name != expected_repository:
        raise ValueError("source workflow run repository does not match the recovery repository")
    if metadata.path.split("@", maxsplit=1)[0] != _PANEL_NULL_WORKFLOW:
        raise ValueError("source workflow run did not execute the panel-null workflow")
    if metadata.event != "workflow_dispatch":
        raise ValueError("source workflow run was not manually dispatched")
    if metadata.status != "completed":
        raise ValueError("source workflow run is not complete")
    if metadata.head_sha != calibration.cohort.code_revision:
        raise ValueError("source workflow run revision does not match the measurement artifact")


def recover_panel_null_measurement(
    source_path: Path,
    output_path: Path,
    *,
    run_metadata_path: Path,
    expected_repository: str,
    expected_run_id: int,
    expected_run_attempt: int,
) -> PanelNullCalibration:
    """Validate and atomically publish the exact completed artifact bytes."""
    source = Path(source_path)
    output = Path(output_path)
    payload = source.read_bytes()
    calibration = PanelNullCalibration.model_validate_json(payload)
    canonical_payload = (calibration.model_dump_json(indent=2) + "\n").encode()
    if payload != canonical_payload:
        raise ValueError("source is not a canonical panel-null calibration artifact")
    metadata = _WorkflowRunMetadata.model_validate_json(Path(run_metadata_path).read_bytes())
    _validate_source_run(
        calibration,
        metadata,
        expected_repository=expected_repository,
        expected_run_id=expected_run_id,
        expected_run_attempt=expected_run_attempt,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(dir=output.parent, prefix=f".{output.name}.", delete=False) as temp:
            temp.write(payload)
            temp.flush()
            os.fsync(temp.fileno())
            temporary_path = Path(temp.name)
        os.replace(temporary_path, output)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return calibration


def main() -> None:
    if len(sys.argv) != 7:
        raise SystemExit(__doc__)
    calibration = recover_panel_null_measurement(
        Path(sys.argv[1]),
        Path(sys.argv[6]),
        run_metadata_path=Path(sys.argv[2]),
        expected_repository=sys.argv[3],
        expected_run_id=int(sys.argv[4]),
        expected_run_attempt=int(sys.argv[5]),
    )
    print(
        "recovered complete panel-null measurement: "
        f"{len(calibration.replicates)} panels at {calibration.cohort.code_revision}"
    )


if __name__ == "__main__":
    main()
