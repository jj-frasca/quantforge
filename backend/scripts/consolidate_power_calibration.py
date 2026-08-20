"""Collect a power sweep's cells into one committed record (ADR-053).

Usage: PYTHONPATH=. uv run python scripts/consolidate_power_calibration.py CELL_DIR [OUT_JSON]

Reads every *.json cell in CELL_DIR — one `PowerCalibration` per swept phi or half-life — orders
them, and refuses any sweep whose cells plant different processes, resolve different search
procedures, or were measured on different history lengths. Those are not points on one curve.

Unlike the null consolidator this does NOT merge: each cell is judged at its own N against its own
stated effect size, so pooling them would report a detection rate for no effect size at all. This
script is the sole writer of its output file (ADR-030).
"""

import sys
from pathlib import Path

from app.research.lab.calibration import PowerCalibration, PowerSweep, collect_power_sweep


def _report(sweep: PowerSweep) -> None:
    print(f"planted process     : {sweep.edge}")
    print(f"gate config version : {sweep.gate_config_version}")
    print(f"search config version: {sweep.search_config_version}")
    print(f"bars per symbol     : {sweep.n_bars} (the hunt's own history length)")
    # ADR-055: `oracle` is gross and `net` charges the same 10bp turnover cost every catalog
    # finalist paid. `capture` divides a net numerator by a gross denominator and is kept only
    # because ADR-041/042/045 published it; `net cap` is the comparable ratio.
    print(
        f"{'sweep':>8}{'n':>6}{'oracle':>9}{'net':>8}{'detect':>9}{'bar':>7}"
        f"{'capture':>9}{'net cap':>9}  DSR passes"
    )
    for cell in sweep.cells:
        key = cell.phi if cell.phi is not None else cell.half_life
        percentiles = cell.oracle_sharpe_percentiles
        oracle = percentiles[0] if percentiles else float("nan")
        net_percentiles = cell.net_oracle_sharpe_percentiles
        net_oracle = f"{net_percentiles[0]:+.2f}" if net_percentiles else "n/a"
        capture = cell.capture_ratio
        net_capture = cell.net_capture_ratio
        print(
            f"{key:>8}{cell.n_symbols:>6}{oracle:>+9.2f}{net_oracle:>8}"
            f"{cell.detection_rate:>8.0%}{cell.n_clear_deflation_bar:>7}"
            f"{(f'{capture:.1%}' if capture is not None else 'n/a'):>9}"
            f"{(f'{net_capture:.1%}' if net_capture is not None else 'n/a'):>9}"
            f"  {cell.gate_pass_counts.get('dsr', 'n/a')}/{cell.n_symbols}"
        )


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    cell_dir = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    paths = sorted(cell_dir.glob("*.json"))
    if not paths:
        raise SystemExit(f"no cell files in {cell_dir}")
    sweep = collect_power_sweep(
        [PowerCalibration.model_validate_json(p.read_text()) for p in paths]
    )

    print("=" * 78)
    print("QUANTFORGE — gate power calibration (ADR-041/042/053)")
    print("=" * 78)
    print(f"collected {len(paths)} cell(s) from {cell_dir}")
    _report(sweep)

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(sweep.model_dump_json(indent=2) + "\n")
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
