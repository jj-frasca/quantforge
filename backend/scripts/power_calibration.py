"""Power calibration driver (ADR-041) — the Type-II half of ADR-036.

Usage: PYTHONPATH=. uv run python scripts/power_calibration.py [N_SYMBOLS] [SEED] [--phi P]
           [--shard I/N] [--out PATH]
       (default: 50 symbols, seed 0, phi -0.20, whole run, print only)

Plants an AR(1) edge of known strength, runs the UNMODIFIED search + gate, and reports how often
it is DETECTED. `phi < 0` is mean reversion, `phi > 0` is trend persistence — sweep both signs, or
a phi the catalog cannot trade measures as zero power and tells you only that the catalog has a
blind spot there.

Read the two tiers separately: `DETECTION` is power of the gate as such; `clear ADR-018 bar` is
power against the standard the project actually holds itself to, and it is the number that
interprets the standing "0 of 40 graduates clear the bar" finding.

An AR(1) edge is stationary and always-on, so this is an UPPER BOUND on power against real,
intermittent edges (ADR-041 §"The honest limits"). Expensive (one full search per symbol) and NEVER
in CI; writes no pooled data — a synthetic symbol is not a hypothesis about a real one.
"""

import sys
from pathlib import Path
from statistics import median

from app.research.lab.calibration import PowerCalibration, autocorrelated_edge, measure_power
from app.research.strategies.catalog import STRATEGY_CATALOG

# ADR-051: the length a real hunt actually sees (scripts/shard_hunt.py starts at 2005-01-01, so a
# long-lived name carries ~5400 trading days by 2026), matching the null driver so power and Type-I
# error stay comparable. The previous 3000 measured power on 55% of the hunt's history against a
# MinTRL requirement that grows with the trial count but not with the record, which makes a zero
# result a lower bound rather than a finding. `--n-bars` overrides it.
N_BARS = 5400


def _flag(name: str) -> str | None:
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


def _report(result: PowerCalibration) -> None:
    if result.phi is None:
        raise ValueError("AR(1) power result is missing phi")
    print(
        f"planted phi         : {result.phi:+.3f} ({'mean-reverting' if result.phi < 0 else 'trending'})"
    )
    print(f"gate config version : {result.gate_config_version}")
    print(f"search config version: {result.search_config_version}")
    print(f"adaptive refinement : {result.refine} (span {result.refine_span:.2f})")
    print(f"symbols searched    : {result.n_symbols}")
    if result.n_bars:
        print(f"bars per symbol     : {median(result.n_bars):.0f} (the hunt's own history length)")
    print(f"detected            : {result.n_detected}")
    print(f"DETECTION RATE      : {result.detection_rate:.1%}  <- power of the gate as such")
    if result.gate_pass_counts:
        passes = " | ".join(
            f"{name} {count}/{result.n_symbols}" for name, count in result.gate_pass_counts.items()
        )
        print(f"gate component pass : {passes}")
    print(
        f"clear ADR-018 bar   : {result.n_clear_deflation_bar} (bar {result.deflation_bar:.2f})"
        "  <- power against the standard we actually hold to"
    )
    pct = result.oracle_sharpe_percentiles
    if pct is not None:
        print(
            f"oracle Sharpe       : median {pct[0]:+.2f} | p95 {pct[1]:+.2f} | max {pct[2]:+.2f} "
            "(the effect size actually planted, measured not derived)"
        )
    capture = result.capture_ratio
    if capture is not None:
        print(
            f"CAPTURE UPPER BOUND : {capture:.1%}  <- median finalist in-sample Sharpe / "
            "median oracle Sharpe (selection-biased)"
        )
    if result.errors:
        print(f"unsearchable        : {len(result.errors)} symbol(s)")


def main() -> None:
    shard_spec = _flag("--shard")
    out = _flag("--out")
    phi_flag = _flag("--phi")
    n_bars_flag = _flag("--n-bars")
    consumed = {shard_spec, out, phi_flag, n_bars_flag} - {None}
    positional = [a for a in sys.argv[1:] if not a.startswith("--") and a not in consumed]

    n_symbols = int(positional[0]) if positional else 50
    seed = int(positional[1]) if len(positional) > 1 else 0
    phi = float(phi_flag) if phi_flag else -0.20
    shard, n_shards = (int(x) for x in shard_spec.split("/")) if shard_spec else (0, 1)
    n_bars = int(n_bars_flag) if n_bars_flag else N_BARS
    indices = [i for i in range(n_symbols) if i % n_shards == shard]

    frames = {f"EDGE{i:04d}": autocorrelated_edge(n_bars, seed=seed + i, phi=phi) for i in indices}
    strategies = [entry.name for entry in STRATEGY_CATALOG]
    print(
        f"measuring power against {len(indices)} of {n_symbols} planted-edge symbols x {n_bars} "
        f"bars over {len(strategies)} strategies (phi {phi:+.3f}, seed {seed}, "
        f"shard {shard}/{n_shards})...\n"
    )
    result = measure_power(frames, strategies, phi=phi)
    _report(result)

    if out:
        Path(out).write_text(result.model_dump_json(indent=2) + "\n")
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
