# ADR-132: Validate ingestion request ranges before adapter access

- **Status:** Accepted
- **Date:** 2026-09-23
- **Deciders:** Codex autonomous session 11 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-062
- **Extends:** ADR-005 and ADR-119

## Context

ADR-119 binds returned bars to the requested half-open `[start, end)` interval, but neither the
ingestion pipeline nor its HTTP request model validates the interval itself. The pipeline calls the
adapter first. Naive datetimes can reach an external vendor and later trigger an incidental Python
comparison error against UTC bars; equal or reversed bounds rely on vendor-specific behavior. A
request cannot serve as acquisition provenance unless it denotes one non-empty interval before any
external access occurs.

## Options Considered

1. **Validate timezone awareness and strict ordering at both the pipeline and API boundaries.**
   - Pro: the pipeline remains safe for every direct caller; HTTP callers receive a stable 422
     response; no invalid request reaches an adapter.
   - Con: the same small invariant is enforced at two public boundaries.
2. **Validate only in the API request model.**
   - Pro: malformed HTTP requests fail declaratively before endpoint execution.
   - Con: direct pipeline callers, including research and internal API helpers, can still perform
     vendor I/O with invalid bounds.
3. **Let each adapter or vendor validate its inputs.**
   - Pro: no additional local validation code.
   - Con: behavior differs by vendor and may consume network retries before failure; the platform
     loses one stable request contract.

## Decision

Require both bounds to be timezone-aware and require `start < end` before adapter access in
`DataIngestionPipeline.ingest`. Invalid direct calls raise `ValueError` without fetching or
persisting a quality report, because no acquisition occurred. Apply the same invariant to
`IngestRequest` so malformed HTTP requests return Pydantic/FastAPI validation errors before
dependency execution. Aware non-UTC offsets remain valid instants; ADR-119 continues to compare
the exact supplied bounds against canonical UTC bars. No data-quality heuristic or threshold
changes.

## Consequences

- Naive, zero-width, and reversed ingestion requests fail deterministically before external I/O.
- API and direct pipeline callers share the same interval semantics.
- Invalid requests do not create misleading quality reports for evidence that was never fetched.
- Other API request models remain separate consumers and should adopt the shared invariant when
  their cache/fetch paths are audited; this ADR does not silently broaden its implementation scope.

## Reversal

Remove the preflight and API model validation. That would restore vendor-dependent request
semantics and external access before local validation and is not recommended.
