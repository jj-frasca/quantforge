"""Read two committed power sweeps against each other (ADR-057 amendment).

Usage: PYTHONPATH=. uv run python scripts/compare_power_sweeps.py BEFORE.json AFTER.json

Both files are `PowerSweep` records — e.g. `data/power_calibration/band_reversion.json` at two
commits. The comparison refuses a pair that plants different processes, was measured at different
history lengths, or was judged by different gate configs, and it also refuses a pair with the SAME
search family: with no catalog change between them there is nothing a capture delta could mean.

`attributable` is the column to read. A capture rise is attributable to a catalog change only when
the finalist mix moved with it — otherwise the rise is the in-sample maximum over a larger grid.
"""

import sys
from pathlib import Path

from app.research.lab.calibration import PowerSweep, compare_power_sweeps


def _pct(value: float | None) -> str:
    return f"{value:+.1%}" if value is not None else "n/a"


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    before = PowerSweep.model_validate_json(Path(sys.argv[1]).read_text())
    after = PowerSweep.model_validate_json(Path(sys.argv[2]).read_text())
    rows = compare_power_sweeps(before, after)

    print("=" * 78)
    print(f"QUANTFORGE — paired power sweep, planted process: {before.edge} (ADR-057)")
    print("=" * 78)
    print(f"before search family : {before.search_config_version}")
    print(f"after  search family : {after.search_config_version}")
    print(f"bars per symbol      : {before.n_bars}")
    print(
        f"{'cell':>8}{'net cap':>10}{'->':>4}{'net cap':>10}{'delta':>9}{'detect':>9}  attributable"
    )
    for row in rows:
        print(
            f"{row.key:>8}{_pct(row.net_capture_before):>10}{'->':>4}"
            f"{_pct(row.net_capture_after):>10}{_pct(row.net_capture_delta):>9}"
            f"{_pct(row.detection_delta):>9}  "
            f"{'yes' if row.attributable else 'no — ' + (row.reason or '')}"
        )
        if row.finalists_before or row.finalists_after:
            print(f"{'':>8}  finalists {row.finalists_before} -> {row.finalists_after}")


if __name__ == "__main__":
    main()
