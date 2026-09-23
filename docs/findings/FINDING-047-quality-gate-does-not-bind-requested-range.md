# FINDING-047: Quality reports do not bind bars to the requested time range

- **Severity:** High
- **Status:** Resolved by ADR-119
- **Found:** 2026-09-23, Codex autonomous session 10
- **Affects:** `DataQualityEngine`, `DataIngestionPipeline`, adapter half-open range contract

## Finding

Every `DataSourceAdapter` promises canonical bars for the half-open interval `[start, end)`, and
every repository read is required to use that same range convention. The ingestion pipeline passes
the requested bounds to the adapter but never verifies the returned timestamps. A buggy adapter,
pagination overlap, inclusive vendor end date, or timezone-boundary error can therefore return bars
before `start` or at/after `end`; those bars receive a passing quality report and are stored.

Subsequent callers querying the requested interval may not see the extra rows, but later wider
queries can consume evidence that was never requested or quality-bound to its acquisition window.
The persisted report contains no issue identifying the adapter contract breach. This makes cache
contents depend on vendor overfetch behavior and breaks the documented half-open provenance rule.

## Required correction

Have the ingestion pipeline pass the requested bounds into the quality boundary. For non-empty
input, reject any timestamp outside `[start, end)` as a structural `range_mismatch` error before
sample-size or pairwise heuristics; persist the failed report and store no bars. Direct engine calls
without request bounds retain their current behavior. No heuristic threshold changes.
