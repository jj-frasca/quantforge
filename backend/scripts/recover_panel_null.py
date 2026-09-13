"""Publish one already completed panel-null artifact without remeasurement (ADR-087).

Usage: PYTHONPATH=. uv run python scripts/recover_panel_null.py SOURCE_JSON OUT_JSON

The source must deserialize as a complete ``PanelNullCalibration``. Validation finishes before the
destination is touched, then the exact source bytes replace the generated-data path atomically.
Only the manual panel-null workflow may invoke this against ``data/`` under ADR-030.
"""

import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.research.lab.panel_null import PanelNullCalibration


def recover_panel_null_measurement(
    source_path: Path,
    output_path: Path,
) -> PanelNullCalibration:
    """Validate and atomically publish the exact completed artifact bytes."""
    source = Path(source_path)
    output = Path(output_path)
    payload = source.read_bytes()
    calibration = PanelNullCalibration.model_validate_json(payload)
    canonical_payload = (calibration.model_dump_json(indent=2) + "\n").encode()
    if payload != canonical_payload:
        raise ValueError("source is not a canonical panel-null calibration artifact")

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
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    calibration = recover_panel_null_measurement(Path(sys.argv[1]), Path(sys.argv[2]))
    print(
        "recovered complete panel-null measurement: "
        f"{len(calibration.replicates)} panels at {calibration.cohort.code_revision}"
    )


if __name__ == "__main__":
    main()
