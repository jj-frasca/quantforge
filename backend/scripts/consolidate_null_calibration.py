"""Merge sharded null-calibration runs into one measurement (ADR-037).

Usage: PYTHONPATH=. uv run python scripts/consolidate_null_calibration.py SHARD_DIR [OUT_JSON]

Reads every *.json shard in SHARD_DIR, merges them at the COMBINED symbol count — which re-judges
each false graduate against the ADR-018 bar the full run implies, not its own shard's smaller bar —
and prints the headline. This script is the sole writer of data/null_calibration.json (ADR-030).
"""

import sys
from pathlib import Path

from app.research.lab.calibration import NullCalibration, merge_calibrations


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    shard_dir = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    paths = sorted(shard_dir.glob("*.json"))
    if not paths:
        raise SystemExit(f"no shard files in {shard_dir}")
    shards = [NullCalibration.model_validate_json(p.read_text()) for p in paths]
    merged = merge_calibrations(shards)

    print("=" * 78)
    print("QUANTFORGE — null-model gate calibration (ADR-036/037)")
    print("=" * 78)
    print(f"merged {len(shards)} shard(s) from {shard_dir}")
    print(f"null mode           : {merged.null_mode}")
    print(f"gate config version : {merged.gate_config_version}")
    print(f"symbols searched    : {merged.n_symbols} (no edge by construction)")
    print(f"false graduates     : {merged.n_graduates}")
    print(f"FALSE GRADUATION    : {merged.false_graduation_rate:.2%}  <- Type-I error, whole gate")
    print(f"clear ADR-018 bar   : {merged.n_clear_deflation_bar} (bar {merged.deflation_bar:.2f})")
    print(f"max deflated Sharpe : {merged.max_deflated_sharpe:.3f} (should be <= 0 under the null)")
    if merged.max_holdout_sharpe is not None:
        print(f"max holdout Sharpe  : {merged.max_holdout_sharpe:.2f} (among false graduates)")
    if merged.graduate_symbols:
        print(f"which               : {', '.join(merged.graduate_symbols[:20])}")
    if merged.errors:
        print(f"unsearchable        : {len(merged.errors)} symbol(s)")

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(merged.model_dump_json(indent=2))
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
