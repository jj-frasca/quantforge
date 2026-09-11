"""Merge complete panel-null shards into one validated measurement (ADR-081).

Usage: PYTHONPATH=. uv run python scripts/consolidate_panel_null.py SHARD_DIR [OUT_JSON]

Reads every JSON shard in SHARD_DIR, rejects missing/duplicate panel indices or identity drift,
prints the pre-registered ADR-081/082 inference, and optionally writes the complete artifact.
This script is the sole writer of data/panel_null_calibration/ under ADR-030.
"""

import sys
from pathlib import Path

from app.research.lab.panel_null import (
    PanelDiagnosticInference,
    infer_panel_null,
    load_panel_null_shard,
    merge_panel_null_shards,
)


def _print_diagnostic(label: str, result: PanelDiagnosticInference | None) -> None:
    if result is None:
        print(f"{label:<22}: NOT MEASURED")
        return
    print(
        f"{label:<22}: real {result.real_statistic:+.3f} | "
        f"null [{result.null_p025:+.3f}, {result.null_p975:+.3f}] | "
        f"p {result.two_sided_p_value:.4f} | {result.resolution}"
    )


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    shard_dir = Path(sys.argv[1])
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    paths = sorted(shard_dir.glob("*.json"))
    if not paths:
        raise SystemExit(f"no shard files in {shard_dir}")
    calibration = merge_panel_null_shards([load_panel_null_shard(path) for path in paths])
    inference = infer_panel_null(calibration)

    print("=" * 78)
    print("QUANTFORGE — replicated correlated panel null (ADR-081/082)")
    print("=" * 78)
    print(f"merged shards         : {len(paths)}")
    print(f"whole-panel replicates: {len(calibration.replicates)}")
    print(f"frozen symbols        : {len(calibration.cohort.symbols)}")
    print(f"source digest         : {calibration.cohort.source_sha256}")
    print(f"search config version : {calibration.cohort.search_config_version}")
    print(f"gate config version   : {calibration.cohort.gate_config_version}")
    _print_diagnostic("walk-forward excess", inference.walk_forward)
    _print_diagnostic("purged-CV excess", inference.purged_cv)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(calibration.model_dump_json(indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {output}")


if __name__ == "__main__":
    main()
