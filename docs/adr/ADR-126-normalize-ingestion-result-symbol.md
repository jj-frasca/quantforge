# ADR-126: Normalize `IngestionResult.symbol`

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** Claude autonomous session 104
- **Resolves:** FINDING-054

## Context

`DataIngestionPipeline.ingest()` built its `IngestionResult` from the raw, unnormalized `symbol`
argument, while `DataQualityEngine.check()` (called on the same argument, one line earlier)
normalizes it (`strip().upper()`) and stamps that onto the attached `DataQualityReport.symbol`. The
two symbol fields on one `IngestionResult` — and on `POST /api/v1/ingest`'s response body — could
therefore disagree in case for any non-canonical-case or whitespace-padded request.

## Options Considered

1. **Normalize `symbol` once when constructing `IngestionResult`, mirroring
   `DataQualityEngine.check()`'s own internal normalization.**
   - Pro: smallest possible fix — one field, one call site. Matches the exact normalization the
     quality engine, both repository implementations, and `GET /api/v1/bars` already apply.
     `adapter.fetch_price_bars(symbol, ...)` keeps receiving the original raw argument, so no
     change to the external vendor-facing call's behavior.
   - Con: none identified.
2. **Normalize `symbol` at the very top of `ingest()` and use the normalized value everywhere,
   including the adapter call.**
   - Con: changes what string reaches `adapter.fetch_price_bars` for every existing caller, a
     larger behavioral surface than the actual bug (an output-field mismatch) requires touching —
     vendor ticker lookups are typically case-insensitive, but this changes network-call input
     unnecessarily to fix a response-body inconsistency.
3. **Normalize at the API layer (`ingest.py`'s router function) instead of the pipeline.**
   - Con: `DataIngestionPipeline` is called directly by other code paths too (not just the router);
     fixing it at the pipeline level covers every caller instead of just the one endpoint.

Chose option 1: fixes the actual inconsistency at its source, with no behavior change beyond the
one output field.

## Decision

`DataIngestionPipeline.ingest()`'s `IngestionResult` construction changes from `symbol=symbol` to
`symbol=symbol.strip().upper()`. No change to what's passed to `adapter.fetch_price_bars`.

## Consequences

- `IngestionResult.symbol` (and therefore `POST /api/v1/ingest`'s response) always matches
  `quality_report.symbol` on the same result, for any input casing/whitespace.
- Matches `GET /api/v1/bars`'s existing response normalization, so the two endpoints agree on how
  they echo a symbol back.

## Reversal

Revert to `symbol=symbol`. Not recommended — reintroduces FINDING-054's two-symbol-fields
inconsistency on one response body.
