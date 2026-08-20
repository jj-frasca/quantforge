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

from app.research.lab.calibration import PowerCalibration, autocorrelated_edge, measure_power
from app.research.strategies.catalog import STRATEGY_CATALOG

# Same shape a real hunt sees, matching the null driver so power and Type-I error are comparable.
N_BARS = 3000


def _flag(name: str) -> str | None:
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


def _report(result: PowerCalibration) -> None:
    print(
        f"planted phi         : {result.phi:+.3f} ({'mean-reverting' if result.phi < 0 else 'trending'})"
    )
    print(f"gate config version : {result.gate_config_version}")
    print(f"search config version: {result.search_config_version}")
    print(f"symbols searched    : {result.n_symbols}")
    print(f"detected            : {result.n_detected}")
    print(f"DETECTION RATE      : {result.detection_rate:.1%}  <- power of the gate as such")
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
    if result.errors:
        print(f"unsearchable        : {len(result.errors)} symbol(s)")


def main() -> None:
    shard_spec = _flag("--shard")
    out = _flag("--out")
    phi_flag = _flag("--phi")
    consumed = {shard_spec, out, phi_flag} - {None}
    positional = [a for a in sys.argv[1:] if not a.startswith("--") and a not in consumed]

    n_symbols = int(positional[0]) if positional else 50
    seed = int(positional[1]) if len(positional) > 1 else 0
    phi = float(phi_flag) if phi_flag else -0.20
    shard, n_shards = (int(x) for x in shard_spec.split("/")) if shard_spec else (0, 1)
    indices = [i for i in range(n_symbols) if i % n_shards == shard]

    frames = {f"EDGE{i:04d}": autocorrelated_edge(N_BARS, seed=seed + i, phi=phi) for i in indices}
    strategies = [entry.name for entry in STRATEGY_CATALOG]
    print(
        f"measuring power against {len(indices)} of {n_symbols} planted-edge symbols x {N_BARS} "
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
