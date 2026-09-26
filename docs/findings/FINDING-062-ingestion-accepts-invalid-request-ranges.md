# FINDING-062: Ingestion accepts invalid request ranges before adapter access

- **Severity:** High
- **Status:** Resolved by ADR-132
- **Found:** 2026-09-23
- **Area:** Data ingestion request identity

## Finding

`DataIngestionPipeline.ingest` calls `fetch_price_bars` before proving that its request bounds are
timezone-aware or that `start < end`. The ingest API schema applies the same omission. A naive
bound can therefore reach the vendor and later fail through an incidental aware/naive comparison,
while zero-width and reversed ranges receive vendor-dependent behavior. None is an auditable data
request under the half-open `[start, end)` contract.

## Impact

- Invalid requests can perform external I/O before failing.
- The same request can return empty data, raise a vendor-specific exception, or fail later in the
  quality engine depending on the adapter.
- API callers do not receive a stable validation response for malformed intervals.
- ADR-119 proves returned bars belong to a request but does not prove that the request itself is a
  valid interval.

## Required correction

Validate request bounds before adapter access at the pipeline boundary, require timezone-aware
datetimes with `start < end`, and mirror the contract in the ingest request model so malformed HTTP
requests return validation errors. Preserve ADR-119's returned-evidence check and every heuristic
threshold.

## Resolution

Resolved by ADR-132. The pipeline now validates timezone awareness and strict ordering before
adapter access; the ingest API applies the same invariant during request-model validation.
