"""Null-model gate calibration driver (ADR-036, sharded per ADR-037).

Usage: PYTHONPATH=. uv run python scripts/null_calibration.py [N_SYMBOLS] [SEED]
           [--bootstrap SYM] [--shard I/N] [--out PATH]
       (default: 100 null symbols, seed 0, iid-normal null, whole run, print only)

Runs the UNMODIFIED search + graduation gate over a universe with no edge by construction and
reports how often it graduates something — a measured Type-I error for the whole pipeline. The
`--bootstrap SYM` mode resamples a real symbol's own bars iid with replacement, so the null keeps
that name's fat tails, gaps and realized volatility while carrying zero serial structure.

`--shard I/N` takes every Nth null symbol of the SAME global sequence (seed = SEED + global index),
so the union of all N shards is bit-for-bit the run one process would have produced; merge them
with scripts/consolidate_null_calibration.py, which re-judges every false graduate at the combined
symbol count.

Expensive (one full search per null symbol) and NEVER in CI — CI gets the small seeded unit test in
tests/unit/test_null_calibration.py. Writes no pooled data: a null experiment is not a hypothesis
about a real symbol and must never reach the research pool (ADR-036).
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from app.data.sources.retry import CLOUD
from app.data.sources.yfinance import YFinanceAdapter
from app.research.frames import bars_to_frame
from app.research.lab.calibration import (
    NullCalibration,
    bootstrap_null,
    calibrate_gate,
    drop_incomplete_bars,
    iid_normal_null,
)
from app.research.strategies.catalog import STRATEGY_CATALOG

START = datetime(2005, 1, 1, tzinfo=UTC)
# Matches the shape a real hunt sees: ~12 years, so the 20% holdout clears the 252-bar floor with
# room to spare and MinTRL is reachable — a null run must face the same bar a real symbol does.
N_BARS = 3000


def _source_frame(symbol: str) -> pd.DataFrame:
    adapter = YFinanceAdapter(retry=CLOUD)
    now = datetime.now(UTC)
    # Today's bar is still forming; resampling it makes the bootstrap null drift between two runs
    # on the same day, and a calibration is supposed to be a property of the GateConfig version.
    return drop_incomplete_bars(
        bars_to_frame(adapter.fetch_price_bars(symbol, START, now)), asof=now
    )


def _flag(name: str) -> str | None:
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


def _report(result: NullCalibration) -> None:
    print(f"null mode           : {result.null_mode}")
    print(f"gate config version : {result.gate_config_version}")
    print(f"search config version: {result.search_config_version}")
    print(f"symbols searched    : {result.n_symbols}")
    print(f"graduates           : {result.n_graduates}")
    print(f"FALSE GRADUATION    : {result.false_graduation_rate:.1%}  <- Type-I error, whole gate")
    print(f"clear ADR-018 bar   : {result.n_clear_deflation_bar} (bar {result.deflation_bar:.2f})")
    print(f"max deflated Sharpe : {result.max_deflated_sharpe:.3f} (should be <= 0 under the null)")
    if result.max_holdout_sharpe is not None:
        print(f"max holdout Sharpe  : {result.max_holdout_sharpe:.2f} (among false graduates)")
    if result.graduate_symbols:
        print(f"false graduates     : {', '.join(result.graduate_symbols[:20])}")
    if result.errors:
        print(f"unsearchable        : {len(result.errors)} symbol(s)")
    for label, pct in (
        ("walk-fwd OOS Sharpe", result.walk_forward_null_percentiles),
        ("purged-CV OOS Sharpe", result.purged_cv_null_percentiles),
    ):
        if pct is not None:
            print(f"{label:<20}: median {pct[0]:+.3f} | p95 {pct[1]:+.3f} | max {pct[2]:+.3f}")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    shard_spec = _flag("--shard")
    bootstrap_symbol = _flag("--bootstrap")
    out = _flag("--out")
    consumed = {shard_spec, bootstrap_symbol, out} - {None}
    positional = [a for a in args if a not in consumed]

    n_symbols = int(positional[0]) if positional else 100
    seed = int(positional[1]) if len(positional) > 1 else 0
    shard, n_shards = (int(x) for x in shard_spec.split("/")) if shard_spec else (0, 1)
    indices = [i for i in range(n_symbols) if i % n_shards == shard]

    if bootstrap_symbol:
        symbol = bootstrap_symbol.upper()
        source = _source_frame(symbol)
        print(f"bootstrap null from {symbol}: {len(source)} real bars resampled iid\n")
        frames = {f"NULL{i:04d}": bootstrap_null(source, N_BARS, seed=seed + i) for i in indices}
        mode = f"bootstrap:{symbol}"
    else:
        frames = {f"NULL{i:04d}": iid_normal_null(N_BARS, seed=seed + i) for i in indices}
        mode = "iid_normal"

    strategies = [entry.name for entry in STRATEGY_CATALOG]
    print(
        f"calibrating the gate against {len(indices)} of {n_symbols} null symbols x {N_BARS} bars "
        f"over {len(strategies)} strategies (seed {seed}, shard {shard}/{n_shards})...\n"
    )
    result = calibrate_gate(frames, strategies, null_mode=mode)
    _report(result)

    if out:
        Path(out).write_text(result.model_dump_json(indent=2) + "\n")
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
