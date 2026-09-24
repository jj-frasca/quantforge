# FINDING-055: Alpaca adapter can return a bar on/after its own exclusive `end`

- **Severity:** High
- **Status:** Resolved by ADR-127
- **Found:** 2026-09-24, autonomous session 104 (background audit of `backend/app/data/sources/
  {alpaca,base}.py`, `alpaca.py` cold since 2026-07-07)
- **Affects:** `AlpacaDataAdapter.fetch_price_bars` (`app/data/sources/alpaca.py`, ADR-019 follow-on)

## Finding

`DataSourceAdapter.fetch_price_bars` (`app/data/sources/base.py`) documents its contract exactly:
"Return canonical PriceBars for the half-open range `[start, end)`." `DataQualityEngine.check`
enforces this at the pipeline boundary (`expected_start <= bar.timestamp_utc < expected_end`,
ADR-119, landed earlier the same day as this finding).

`AlpacaDataAdapter._fetch_bars` sends `end.date().isoformat()` straight through to Alpaca's bars
API with no adjustment. Alpaca documents its `end` query parameter as **inclusive**. Since only the
date portion is sent (no time-of-day precision), a request for the common "give me January"
half-open pattern (`start=2024-01-01, end=2024-02-01`) returns Alpaca's Feb-1 daily bar too — its
timestamp is on Feb 1, which is `>= end`, violating the documented half-open contract.

Nothing in `fetch_price_bars`'s testable path (which just maps and normalizes whatever the injected
fetcher returns) filtered this out — the only place any range-awareness could live is inside the
untested (`pragma: no cover`) network glue `_fetch_bars`, which doesn't adjust for Alpaca's
inclusive `end` either. The existing unit tests never exercised this because the injected fake
fetcher only ever returned bars already inside the requested range.

Given `DataQualityEngine`'s `range_mismatch` check (ADR-119) landed the same day as this finding,
this is now directly reachable in production: any live Alpaca-backed ingest whose fetched range
happens to include a boundary-date bar would now fail the quality gate and be silently refused
storage (`report.passed = False`), rather than the caller getting the data they asked for.

## Reproduction

```python
from app.data.sources.alpaca import AlpacaDataAdapter
from datetime import datetime, UTC

def fake_fetch(symbol, start, end):
    return [
        {"t": "2024-01-15T05:00:00Z", "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.5, "v": 1000},
        {"t": "2024-02-01T05:00:00Z", "o": 103.0, "h": 105.0, "l": 102.0, "c": 104.0, "v": 800},
    ]

adapter = AlpacaDataAdapter("key", "secret", fetcher=fake_fetch)
bars = adapter.fetch_price_bars("AAPL", datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 2, 1, tzinfo=UTC))
# pre-fix: len(bars) == 2, including the Feb-1 bar at/after the exclusive end
```
