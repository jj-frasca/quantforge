# FINDING-054: `IngestionResult.symbol` disagreed with its own `quality_report.symbol`

- **Severity:** Medium
- **Status:** Resolved by ADR-126
- **Found:** 2026-09-24, autonomous session 104 (background audit of `backend/app/api/v1/
  {ingest,bars,strategies}.py`, cold since 2026-05-29 to 2026-06-02)
- **Affects:** `DataIngestionPipeline.ingest` (`app/data/pipelines/ingestion.py`), `POST /api/v1/
  ingest`

## Finding

`DataQualityEngine.check()` normalizes its `symbol` argument internally (`symbol.strip().upper()`)
and stamps that onto `DataQualityReport.symbol`. Both `PriceBarRepository` implementations
(`InMemoryPriceBarRepository.get_bars`, `TimescaleDBPriceBarRepository`) and `GET /api/v1/bars`'s
own response normalize the same way. `DataIngestionPipeline.ingest()`, however, built
`IngestionResult(symbol=symbol, ...)` from the raw, unnormalized argument.

For `POST /api/v1/ingest {"symbol": "aapl"}`, the response body therefore carried two `symbol`
fields that disagreed in case: `{"symbol": "aapl", "quality_report": {"symbol": "AAPL", ...}}`.
Neither matched what a subsequent `GET /api/v1/bars?symbol=aapl` would echo back (`"AAPL"`, per
that endpoint's own normalization). A consumer treating `IngestResponse.symbol` as a correlation or
cache key against `/bars`'s response would see a mismatch for any non-canonical-case or
whitespace-padded request.

Masked in the current repo because the frontend's `DataExplorerPage.tsx` already normalizes the
symbol client-side before calling the API — but any other consumer hitting the endpoint directly
(scripts, Swagger UI, a future integration) with lowercase or whitespace-padded input would trip it.
Both `test_ingestion_pipeline.py` and `test_ingest_endpoint.py` only ever exercised pre-uppercased
`"AAPL"`, so the gap had no test coverage.

## Reproduction

```python
from app.data.pipelines.ingestion import DataIngestionPipeline
# result.symbol == "  aapl  " (raw input), result.quality_report.symbol == "AAPL" (normalized) —
# pre-fix, these disagreed on any non-canonical-case/whitespace symbol.
result = DataIngestionPipeline(adapter, repo).ingest("  aapl  ", start, end)
```
