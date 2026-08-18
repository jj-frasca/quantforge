"""Consolidate the daily discovery matrix (ADR-026).

Usage: PYTHONPATH=. uv run python scripts/consolidate_pool.py SHARD_DIR MAIN_POOL PORTFOLIO

Merges every shard pool JSON in SHARD_DIR into MAIN_POOL (dedup by experiment_id — idempotent), then
promotes the merged pool's graduates into the managed paper book PORTFOLIO once (ADR-020). Committed
by the workflow in a single commit, so N parallel shards never race to write the pool. Local-only /
cloud (live network for promotion's position monitoring); never in CI.
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from app.data.sources.yfinance import YFinanceAdapter
from app.research.frames import bars_to_frame
from app.research.lab.experiment import JsonFileExperimentStore
from app.research.lab.paper import JsonFilePaperPortfolio
from app.research.lab.pool_merge import merge_experiments, prune_pool
from app.research.lab.portfolio_manager import manage_portfolio, newly_promoted

START = datetime(2005, 1, 1, tzinfo=UTC)


def main() -> None:
    shard_dir = Path(sys.argv[1])
    main_pool = Path(sys.argv[2])
    portfolio_path = Path(sys.argv[3])

    merged = JsonFileExperimentStore(main_pool).all()
    shard_files = sorted(shard_dir.glob("*.json"))
    for shard_file in shard_files:
        merged = merge_experiments(merged, JsonFileExperimentStore(shard_file).all())

    # Bound the pool so its JSON stays under GitHub's 100MB file limit (keeps all graduates + recent
    # non-graduates; the max-lifetime trial count is preserved, so the MinTRL bar is unchanged).
    before_prune = len(merged)
    merged = prune_pool(merged)
    main_pool.parent.mkdir(parents=True, exist_ok=True)
    payload = [e.model_dump(mode="json") for e in merged]
    main_pool.write_text(json.dumps(payload, indent=2) + "\n")  # trailing newline (eof-fixer)

    portfolio = JsonFilePaperPortfolio(portfolio_path)
    adapter = YFinanceAdapter()
    now = datetime.now(UTC)

    def frame_provider(symbol: str) -> pd.DataFrame:
        return bars_to_frame(adapter.fetch_price_bars(symbol, START, now))

    graduates = [e for e in merged if e.graduate is not None]
    before = portfolio.positions()
    positions = manage_portfolio(before, graduates, frame_provider, now=now)
    portfolio.save(positions)

    n_open = sum(1 for p in positions if p.status == "open")
    promoted = newly_promoted(before, positions)
    print(
        f"consolidated {len(shard_files)} shard(s) -> {len(merged)} experiments "
        f"(pruned from {before_prune}), {len(graduates)} graduate(s); managed book: {n_open} open"
    )
    if promoted:
        print(f"NEW this run ({len(promoted)} promoted — what just cleared the gate):")
        for p in promoted:
            print(f"  + {p.symbol:<7} {p.strategy_name}")
    else:
        print("no new promotions this run.")


if __name__ == "__main__":
    main()
