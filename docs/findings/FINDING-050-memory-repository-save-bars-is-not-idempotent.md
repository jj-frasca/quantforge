# FINDING-050: In-memory repository's `save_bars` is not idempotent, unlike production

- **Severity:** High
- **Status:** Resolved by ADR-122
- **Found:** 2026-09-24, autonomous session 104 (background audit of `backend/app/data/storage/`,
  cold since 2026-05-29)
- **Affects:** `InMemoryPriceBarRepository.save_bars` (`app/data/storage/memory.py`)

## Finding

`TimescaleDBPriceBarRepository.save_bars` upserts every bar via `session.merge(...)` on the
production primary key `(symbol, timestamp_utc, source)` — its own docstring calls this out as
"idempotent ingestion," and `test_save_bars_is_idempotent`
(`backend/tests/integration/test_timescale_repository.py`) asserts it directly. The two backends
implement the same `PriceBarRepository` Protocol and are meant to be interchangeable: the in-memory
backend is the default for local `uvicorn`/dev (`app/dependencies.py`), the Timescale backend for
production.

`InMemoryPriceBarRepository.save_bars` instead appended every bar to a plain per-symbol list with no
dedup on the same key. Re-saving the same bars (or overlapping bars with the same
`(timestamp_utc, source)`) duplicated them in the store, and `get_bars` returned every duplicate —
diverging silently from the production backend's upsert semantics.

This is reachable, not just theoretical: `backend/app/api/v1/backtest.py`'s `_load_frame` (and the
equivalent in `validation.py`) is a cache-aside loader — on a cache miss (`len(bars) < _MIN_BARS`)
it calls `DataIngestionPipeline.ingest(symbol, start, end)` with the request's own range and then
re-reads. Two requests for overlapping-but-different date ranges (e.g. Jan-Mar, then Feb-Apr) can
each independently miss the cache for their own range and re-ingest, re-saving the Feb-Mar overlap a
second time into the in-memory store. `bars_to_frame` sorts by timestamp but does not dedupe, so a
duplicated day appears twice in the resulting backtest/validation frame — silently double-weighting
that bar's return in Sharpe, drawdown, and PBO/DSR statistics computed downstream.

ADR-118 (2026-09-23, same day) fixed a related but narrower problem — `DataQualityEngine` now
rejects duplicate timestamps *within a single ingest() call's own bar list* — and its Consequences
section states "Same-source duplicates no longer depend on production upsert order or differ from
in-memory behavior." That claim held for within-call duplicates but not for this cross-call
scenario, since each individual `ingest()` call here has no internal duplicate; the duplication only
appears across two separate `save_bars` calls, which ADR-118 did not address.

The gap was also invisible in the test suite: `backend/tests/unit/test_memory_repository.py` had no
idempotency test, while the equivalent integration test for `TimescaleDBPriceBarRepository` did —
the same Protocol had unequal test coverage across its two implementations.

## Reproduction

```python
from app.data.storage.memory import InMemoryPriceBarRepository
from tests.fixtures.synthetic import builders

repo = InMemoryPriceBarRepository()
bars = builders.clean_series(n=10)
repo.save_bars(bars)
repo.save_bars(bars)  # e.g. a second cache-aside re-ingest for an overlapping range
len(repo.get_bars("AAPL", bars[0].timestamp_utc, bars[-1].timestamp_utc))  # -> 20, not 10
```
