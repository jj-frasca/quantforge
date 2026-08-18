"""Consolidate the daily discovery matrix (ADR-026).

Usage: PYTHONPATH=. uv run python scripts/consolidate_pool.py SHARD_DIR POOL_DIR PORTFOLIO

Merges every shard pool JSON in SHARD_DIR into the per-symbol pool POOL_DIR (dedup by
experiment_id — idempotent, ADR-032), then
promotes the merged pool's graduates into the managed paper book PORTFOLIO once (ADR-020). Committed
by the workflow in a single commit, so N parallel shards never race to write the pool. Local-only /
cloud (live network for promotion's position monitoring); never in CI.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from app.data.sources.retry import RetryPolicy
from app.data.sources.yfinance import YFinanceAdapter
from app.research.frames import bars_to_frame
from app.research.lab.experiment import (
    Experiment,
    JsonFileExperimentStore,
    PartitionedExperimentStore,
)
from app.research.lab.paper import JsonFilePaperPortfolio
from app.research.lab.pool_merge import merge_experiments
from app.research.lab.portfolio_manager import manage_portfolio, newly_promoted

START = datetime(2005, 1, 1, tzinfo=UTC)
# ADR-031: same cloud throttle policy as the discovery shards.
CLOUD_RETRY = RetryPolicy(attempts=4, base_delay=5.0, max_delay=60.0, min_interval=1.5)


def main() -> None:
    shard_dir = Path(sys.argv[1])
    pool_dir = Path(sys.argv[2])
    portfolio_path = Path(sys.argv[3])

    pool = PartitionedExperimentStore(pool_dir)
    incoming: list[Experiment] = []
    shard_files = sorted(shard_dir.glob("*.json"))
    for shard_file in shard_files:
        incoming = merge_experiments(incoming, JsonFileExperimentStore(shard_file).all())
    # One partition write per touched symbol; retention is applied by the store (ADR-032), so the
    # pool stays bounded no matter which writer got here.
    pool.extend(incoming)
    merged = pool.all()

    portfolio = JsonFilePaperPortfolio(portfolio_path)
    adapter = YFinanceAdapter(retry=CLOUD_RETRY)
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
        f"({len(incoming)} incoming), {len(graduates)} graduate(s); managed book: {n_open} open"
    )
    if promoted:
        print(f"NEW this run ({len(promoted)} promoted — what just cleared the gate):")
        for p in promoted:
            print(f"  + {p.symbol:<7} {p.strategy_name}")
    else:
        print("no new promotions this run.")


if __name__ == "__main__":
    main()
