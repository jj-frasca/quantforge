"""One shard of the fundamental discovery sweep (ADR-029 Layer 3).

Usage: PYTHONPATH=. uv run python scripts/fundamental_sweep.py SHARD_INDEX N_SHARDS OUT_DIR

Walks shard `SHARD_INDEX` of `N_SHARDS` of the FULL SEC CIK universe (every US public filer, from
SEC's company_tickers map), fetches each company's fundamentals history from EDGAR (free, no key),
computes a `FundamentalRecord` (quality always; value when a recent price is available), and writes
THIS shard's records to OUT_DIR/fundamentals_shard_{index}.json (its own file — no write race). A
matrix of N shards works through the whole universe over time; the consolidation job folds them into
`data/fundamentals_pool.json`. Fundamentals update quarterly, so a slow full sweep + revisit is right.

Live network (EDGAR + best-effort yfinance price); local-only / cloud matrix, never in CI. Per-symbol
errors (ETFs with no 10-K, delisted tickers, EDGAR/yfinance hiccups) are recorded and skipped so one
bad name never crashes the shard — the same resilience the price hunt learned the hard way.
"""

import json
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.data.sources.edgar import SecEdgarFundamentalsSource
from app.data.sources.yfinance import YFinanceAdapter
from app.research.fundamentals.record import FundamentalRecord, compute_fundamental_record
from app.research.lab.sharding import shard_universe

USER_AGENT = "QuantForge research jjfrasca10@gmail.com"
_EDGAR_MIN_INTERVAL_S = 0.15  # SEC asks for <= 10 req/s; stay well under.


def _latest_price(adapter: YFinanceAdapter, symbol: str, now: datetime) -> float | None:
    """Best-effort most-recent close for the value leg. Any failure (rate limit, delisting) -> None,
    which degrades the record to quality-only rather than crashing the sweep."""
    try:
        bars = adapter.fetch_price_bars(symbol, now - timedelta(days=14), now)
    except (ValueError, OSError):
        return None
    return float(bars[-1].close) if bars else None


def main() -> None:
    shard_index = int(sys.argv[1])
    n_shards = int(sys.argv[2])
    out_dir = Path(sys.argv[3])

    edgar = SecEdgarFundamentalsSource(user_agent=USER_AGENT)
    adapter = YFinanceAdapter()
    symbols = shard_universe(edgar.all_tickers(), n_shards, shard_index)
    now = datetime.now(UTC)

    print(
        f"Fundamental sweep shard {shard_index}/{n_shards}: {len(symbols)} companies (EDGAR)...\n"
    )
    records: list[FundamentalRecord] = []
    errors = 0
    for symbol in symbols:
        try:
            history = edgar.fetch_history(symbol)
        except (ValueError, OSError, KeyError):
            errors += 1
            continue
        finally:
            time.sleep(_EDGAR_MIN_INTERVAL_S)
        if not history.years:
            continue  # no annual fundamentals (ETF/index) -> nothing to score
        price = _latest_price(adapter, symbol, now)
        records.append(compute_fundamental_record(history, price))

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"fundamentals_shard_{shard_index}.json"
    payload = [r.model_dump(mode="json") for r in records]
    out_file.write_text(json.dumps(payload, indent=2) + "\n")

    scored = sum(1 for r in records if r.quality_score is not None)
    print(
        f"shard {shard_index}: {len(records)} record(s) ({scored} scored), {errors} error(s) "
        f"-> {out_file}"
    )


if __name__ == "__main__":
    main()
