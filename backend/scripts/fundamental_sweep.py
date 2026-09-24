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
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from app.data.fundamentals import FundamentalsHistory
from app.data.sources.edgar import SecEdgarFundamentalsSource
from app.data.sources.retry import CLOUD
from app.data.sources.yfinance import YFinanceAdapter
from app.research.fundamentals.record import FundamentalRecord, compute_fundamental_record
from app.research.lab.sharding import shard_universe
from app.research.valuation.price_join import attach_fiscal_year_prices

USER_AGENT = "QuantForge research jjfrasca10@gmail.com"
_EDGAR_MIN_INTERVAL_S = 0.15  # SEC asks for <= 10 req/s; stay well under.


def _price_series(
    adapter: YFinanceAdapter, symbol: str, since: date, now: datetime
) -> list[tuple[date, float]]:
    """Best-effort ascending (date, close) series from `since` to `now`, for joining onto each
    fiscal year's period end via `attach_fiscal_year_prices` (ADR-022/FINDING-052). Any failure
    (rate limit, delisting) -> empty list, which degrades the record to quality-only rather than
    crashing the sweep."""
    start = datetime.combine(since, datetime.min.time(), tzinfo=UTC)
    try:
        bars = adapter.fetch_price_bars(symbol, start, now)
    except (ValueError, OSError):
        return []
    # attach_fiscal_year_prices/asof_close require ascending order and raise otherwise; don't trust
    # the adapter's raw return order (bars_to_frame and the in-memory repository both sort
    # defensively for the same reason rather than assuming vendor order).
    ordered = sorted(bars, key=lambda b: b.timestamp_utc)
    return [(bar.timestamp_utc.date(), float(bar.close)) for bar in ordered]


def _join_prices(
    adapter: YFinanceAdapter, symbol: str, history: FundamentalsHistory, now: datetime
) -> tuple[FundamentalsHistory, float | None]:
    """Fetch a price series spanning `history`'s fiscal years and join it on (ADR-022), so the
    own-history P/E and P/S percentile legs of UndervaluationScore are actually computable —
    passing only the latest close (the prior behavior) left every year's `price` None, which
    `compute_multiples` requires to build its percentile history (FINDING-052). Falls back to a
    14-day latest-close-only window (old behavior, quality-only percentile legs) when no year has
    a `period_end` to anchor the series start on."""
    since = min((y.period_end for y in history.years if y.period_end is not None), default=None)
    if since is None:
        price = _price_series(adapter, symbol, (now - timedelta(days=14)).date(), now)
        return history, (price[-1][1] if price else None)
    closes = _price_series(adapter, symbol, since, now)
    if not closes:
        return history, None
    return attach_fiscal_year_prices(history, closes), closes[-1][1]


def _sic_description(edgar: SecEdgarFundamentalsSource, symbol: str) -> str | None:
    """Best-effort SIC classification (ADR-095). Any failure -> None, same degrade-not-crash shape
    as `_price_series` — a missing classification is not worth losing the whole record over."""
    try:
        return edgar.fetch_sic(symbol)
    except (ValueError, OSError, KeyError):
        return None


def main() -> None:
    shard_index = int(sys.argv[1])
    n_shards = int(sys.argv[2])
    out_dir = Path(sys.argv[3])

    edgar = SecEdgarFundamentalsSource(user_agent=USER_AGENT)
    adapter = YFinanceAdapter(retry=CLOUD)
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
        joined_history, price = _join_prices(adapter, symbol, history, now)
        try:
            sic = _sic_description(edgar, symbol)
        finally:
            time.sleep(_EDGAR_MIN_INTERVAL_S)  # a second EDGAR call per symbol (ADR-095)
        records.append(compute_fundamental_record(joined_history, price, sic))

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
