"""One shard of the daily discovery matrix (ADR-026).

Usage: PYTHONPATH=. uv run python scripts/shard_hunt.py SHARD_INDEX N_SHARDS UNIVERSE_FILE OUT_POOL

Hunts shard `SHARD_INDEX` of `N_SHARDS` (a deterministic round-robin slice of UNIVERSE_FILE) with
the FULL current strategy catalog on max-history daily data, and writes THIS shard's experiments to
OUT_POOL (its own file — no shared-pool write race). The consolidation job merges every shard's
OUT_POOL into the research pool and promotes once. Local-only / cloud matrix (live network); never
in CI.

DATA SOURCE: forces YFinanceAdapter (MinTRL needs 15-20yr; Alpaca IEX is too short — ADR-015).
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from app.data.fundamentals import FundamentalCriteria, FundamentalSnapshot
from app.data.sources.edgar import SecEdgarFundamentalsSource
from app.data.sources.yfinance import YFinanceAdapter
from app.research.frames import bars_to_frame
from app.research.lab.experiment import JsonFileExperimentStore
from app.research.lab.gate import GateConfig
from app.research.lab.sharding import shard_universe
from app.research.lab.universe import run_universe_hunt
from app.research.lab.universe_files import load_universe
from app.research.strategies.catalog import STRATEGY_CATALOG

START = datetime(2005, 1, 1, tzinfo=UTC)
USER_AGENT = "QuantForge research jjfrasca10@gmail.com"


def main() -> None:
    shard_index = int(sys.argv[1])
    n_shards = int(sys.argv[2])
    universe_file = sys.argv[3]
    out_pool = sys.argv[4]

    symbols = shard_universe(load_universe(universe_file), n_shards, shard_index)
    names = [entry.name for entry in STRATEGY_CATALOG]
    adapter = YFinanceAdapter()  # forced: the hunt needs 15-20yr of history.
    edgar = SecEdgarFundamentalsSource(user_agent=USER_AGENT)
    store = JsonFileExperimentStore(Path(out_pool))
    now = datetime.now(UTC)

    def frame_provider(symbol: str) -> pd.DataFrame:
        return bars_to_frame(adapter.fetch_price_bars(symbol, START, now))

    def fundamentals_provider(symbol: str) -> FundamentalSnapshot | None:
        try:
            return edgar.fetch(symbol)
        except (ValueError, OSError):
            return None  # ETFs/indices have no 10-K revenue

    print(
        f"Shard {shard_index}/{n_shards}: {len(symbols)} symbols x {len(names)} strategies "
        f"(yfinance max history)...\n"
    )
    result = run_universe_hunt(
        symbols,
        names,
        frame_provider,
        fundamentals_provider=fundamentals_provider,
        config=GateConfig(),
        fundamental_criteria=FundamentalCriteria(),
        store=store,
        refine=True,
        rationale=f"daily discovery shard {shard_index}/{n_shards}",
    )
    graduates = [e for e in result.experiments if e.graduate is not None]
    print(
        f"shard {shard_index}: {len(result.experiments)} experiments, {len(graduates)} graduate(s), "
        f"{len(result.errors)} error(s) -> {out_pool}"
    )


if __name__ == "__main__":
    main()
