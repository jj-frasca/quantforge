"""Null-model gate calibration driver (ADR-036).

Usage: PYTHONPATH=. uv run python scripts/null_calibration.py [N_SYMBOLS] [SEED] [--bootstrap SYM]
       (default: 100 null symbols, seed 0, iid-normal null)

Runs the UNMODIFIED search + graduation gate over a universe with no edge by construction and
reports how often it graduates something — a measured Type-I error for the whole pipeline. The
`--bootstrap SYM` mode resamples a real symbol's own bars iid with replacement, so the null keeps
that name's fat tails, gaps and realized volatility while carrying zero serial structure.

Expensive (one full search per null symbol) and NEVER in CI — CI gets the small seeded unit test in
tests/unit/test_null_calibration.py. Writes nothing: a null experiment is not a hypothesis about a
real symbol and must never reach the research pool (ADR-036).
"""

import sys
from datetime import UTC, datetime

import pandas as pd

from app.data.sources.retry import CLOUD
from app.data.sources.yfinance import YFinanceAdapter
from app.research.frames import bars_to_frame
from app.research.lab.calibration import bootstrap_null, calibrate_gate, iid_normal_null
from app.research.strategies.catalog import STRATEGY_CATALOG

START = datetime(2005, 1, 1, tzinfo=UTC)
# Matches the shape a real hunt sees: ~12 years, so the 20% holdout clears the 252-bar floor with
# room to spare and MinTRL is reachable — a null run must face the same bar a real symbol does.
N_BARS = 3000


def _source_frame(symbol: str) -> pd.DataFrame:
    adapter = YFinanceAdapter(retry=CLOUD)
    return bars_to_frame(adapter.fetch_price_bars(symbol, START, datetime.now(UTC)))


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n_symbols = int(args[0]) if args else 100
    seed = int(args[1]) if len(args) > 1 else 0
    bootstrap_symbol = None
    if "--bootstrap" in sys.argv:
        bootstrap_symbol = sys.argv[sys.argv.index("--bootstrap") + 1].upper()

    if bootstrap_symbol:
        source = _source_frame(bootstrap_symbol)
        print(f"bootstrap null from {bootstrap_symbol}: {len(source)} real bars resampled iid\n")
        frames = {
            f"NULL{i:04d}": bootstrap_null(source, N_BARS, seed=seed + i) for i in range(n_symbols)
        }
    else:
        frames = {f"NULL{i:04d}": iid_normal_null(N_BARS, seed=seed + i) for i in range(n_symbols)}

    strategies = [entry.name for entry in STRATEGY_CATALOG]
    print(
        f"calibrating the gate against {n_symbols} null symbols x {N_BARS} bars "
        f"over {len(strategies)} strategies (seed {seed})...\n"
    )
    result = calibrate_gate(frames, strategies)

    print(f"gate config version : {result.gate_config_version}")
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


if __name__ == "__main__":
    main()
