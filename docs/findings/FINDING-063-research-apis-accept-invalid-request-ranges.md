# FINDING-063: Research APIs accept invalid request ranges

- **Severity:** High
- **Status:** Resolved by ADR-133
- **Found:** 2026-09-26
- **Area:** Research API request identity

## Finding

ADR-132 validates the ingest endpoint and direct ingestion pipeline, but the other range-bearing
research APIs define independent unvalidated datetime fields. `/backtest`, `/validate`, and
`/monte-carlo` can reach the cache-aside repository before a miss delegates to the protected
pipeline; `/bars` always queries the repository directly. Naive, zero-width, and reversed ranges
therefore retain repository-dependent behavior instead of one request contract.

## Impact

- Malformed requests can perform repository work or fail through incidental aware/naive datetime
  comparisons rather than returning a stable validation response.
- Cache hits and misses can disagree: only a miss eventually reaches ADR-132's pipeline check.
- The read-only bars API accepts intervals that cannot represent the half-open query contract.
- Equivalent range fields have different semantics across the public API.

## Required correction

Create one shared timezone-aware, strictly ordered range validator and apply it to every public
range-bearing request boundary before repository or adapter access. Preserve aware non-UTC
instants, cache-aside behavior for valid requests, and every data-quality threshold.

## Resolution

Resolved by ADR-133. All public range-bearing APIs now use one shared interval validator before
repository or adapter access.
