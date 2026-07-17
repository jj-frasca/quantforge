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
from app.research.lab.pool_merge import merge_experiments
from app.research.lab.portfolio_manager import manage_portfolio

START = datetime(2005, 1, 1, tzinfo=UTC)


def main() -> None:
    shard_dir = Path(sys.argv[1])
    main_pool = Path(sys.argv[2])
    portfolio_path = Path(sys.argv[3])

    merged = JsonFileExperimentStore(main_pool).all()
    shard_files = sorted(shard_dir.glob("*.json"))
    for shard_file in shard_files:
        merged = merge_experiments(merged, JsonFileExperimentStore(shard_file).all())

    main_pool.parent.mkdir(parents=True, exist_ok=True)
    payload = [e.model_dump(mode="json") for e in merged]
    main_pool.write_text(json.dumps(payload, indent=2) + "\n")  # trailing newline (eof-fixer)

    portfolio = JsonFilePaperPortfolio(portfolio_path)
    adapter = YFinanceAdapter()
    now = datetime.now(UTC)

    def frame_provider(symbol: str) -> pd.DataFrame:
        return bars_to_frame(adapter.fetch_price_bars(symbol, START, now))

    graduates = [e for e in merged if e.graduate is not None]
    positions = manage_portfolio(portfolio.positions(), graduates, frame_provider, now=now)
    portfolio.save(positions)

    n_open = sum(1 for p in positions if p.status == "open")
    print(
        f"consolidated {len(shard_files)} shard(s) -> {len(merged)} experiments, "
        f"{len(graduates)} graduate(s); managed book: {n_open} open"
    )


if __name__ == "__main__":
    main()
