"""Cross-sectional universe hunt driver (ADR-024).

Usage: PYTHONPATH=. uv run python scripts/cross_sectional_hunt.py [SYMBOLS_OR_UNIVERSE.txt]
       (default universe: data/universes/sp500.txt)

Ranks the whole universe each period and goes long the top / short the bottom (cross-sectional
momentum + short-term reversal), realizes ONE dollar-neutral portfolio return series per config,
and runs it through the SAME graduation gate a single-name strategy must clear (DSR/PBO/stability/
MinTRL/holdout/beat-benchmark). Findings accumulate in data/cross_sectional_pool.json so search
effort compounds via the MinTRL flywheel. Local-only / cloud cron (live network); never in CI.

DATA SOURCE (load-bearing): forces YFinanceAdapter — cross-sectional momentum needs a long common
history (lookbacks up to ~252 bars + a MinTRL-worthy holdout), and Alpaca's free IEX feed only
reaches back a few years (ADR-015). Same rationale as scripts/hunt.py.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from app.data.sources.yfinance import YFinanceAdapter
from app.research.cross_sectional.hunt import run_cross_sectional_hunt
from app.research.cross_sectional.store import JsonFileCrossSectionalStore
from app.research.frames import bars_to_frame

DATA = Path(__file__).resolve().parents[2] / "data"
POOL = DATA / "cross_sectional_pool.json"
DEFAULT_UNIVERSE = DATA / "universes" / "sp500.txt"
START = datetime(2005, 1, 1, tzinfo=UTC)


def _resolve_symbols(args: list[str]) -> list[str]:
    """A single .txt path -> one symbol per line; else the args as tickers; else the sp500 file."""
    if len(args) == 1 and args[0].endswith(".txt"):
        path = Path(args[0])
    elif args:
        return [s.strip().upper() for s in args if s.strip()]
    else:
        path = DEFAULT_UNIVERSE
    return [s.strip().upper() for s in path.read_text().splitlines() if s.strip()]


def main() -> None:
    symbols = _resolve_symbols(sys.argv[1:])
    adapter = YFinanceAdapter()  # forced: cross-sectional momentum needs a long common history.
    store = JsonFileCrossSectionalStore(POOL)
    now = datetime.now(UTC)

    def frame_provider(symbol: str) -> pd.DataFrame:
        return bars_to_frame(adapter.fetch_price_bars(symbol, START, now))

    print(f"Cross-sectional hunt over {len(symbols)} symbols (yfinance max history)...\n")
    result = run_cross_sectional_hunt(
        symbols, frame_provider, store=store, rationale="scheduled cross-sectional hunt"
    )
    exp = result.experiment

    print(
        f"panel: {len(exp.universe_symbols)} symbols x {result.panel_bars} bars "
        f"({len(result.errors)} skipped); lifetime trials {exp.lifetime_trials}\n"
    )
    print(f"{'strategy':<14}{'DSR':>7}{'PBO':>7}{'stability':>11}{'obs Sharpe':>12}")
    for trial in sorted(exp.trials, key=lambda t: t.deflated_sharpe, reverse=True):
        print(
            f"{trial.strategy_name:<14}{trial.deflated_sharpe:>7.2f}{trial.pbo:>7.2f}"
            f"{trial.parameter_stability_score:>11.2f}{trial.observed_sharpe:>12.2f}"
        )

    if exp.graduate is not None:
        g = exp.graduate
        print(
            f"\nGRADUATED ✅ {g.strategy_name} {g.parameters} "
            f"holdout Sharpe {g.holdout_sharpe:.2f} (vs equal-weight benchmark)"
        )
    else:
        reasons = exp.best_gate_result.reasons if exp.best_gate_result else []
        print(f"\nno graduate. gate reasons: {'; '.join(reasons) if reasons else '—'}")

    if result.errors:
        shown = list(result.errors.items())[:10]
        print("skipped:", ", ".join(f"{s} ({e})" for s, e in shown))


if __name__ == "__main__":
    main()
