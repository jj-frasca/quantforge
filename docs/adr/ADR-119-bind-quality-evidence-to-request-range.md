# ADR-119: Bind quality evidence to the requested half-open range

- **Status:** Accepted
- **Date:** 2026-09-23
- **Deciders:** Codex autonomous session 10 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-047
- **Extends:** ADR-006 and ADR-118

## Context

The adapter and repository contracts both define time ranges as half-open `[start, end)`, but the
quality gate currently sees only returned bars, symbol, and expected source. It cannot detect an
adapter that overfetches before `start`, treats `end` as inclusive, or maps a vendor timezone across
the requested boundary. The pipeline then stores those out-of-range bars under a passing report.

## Options Considered

1. **Validate returned timestamps at the quality boundary using the pipeline request bounds.**
   - Pro: produces an auditable failed report and blocks all bars before storage; keeps symbol,
     source, calendar, and request-window identity in one structural preflight.
   - Con: extends the quality-engine call with two optional provenance inputs.
2. **Silently filter the adapter result to `[start, end)`.**
   - Pro: callers receive the requested data even when an adapter overfetches.
   - Con: hides a broken adapter contract and lets the report describe a post-fetch transformation
     without recording that evidence was discarded.
3. **Rely on later repository queries to filter the requested range.**
   - Con: the out-of-range bars are still committed and become visible to a later wider query;
     storage is not a substitute for validating acquisition provenance.

## Decision

Add optional `expected_start` and `expected_end` keyword inputs to `DataQualityEngine.check`; they
must be supplied together. `DataIngestionPipeline` always supplies the exact adapter request bounds.
For non-empty input, if any bar fails `expected_start <= timestamp_utc < expected_end`, append one
structural `range_mismatch` error containing the expected bounds and sorted offending timestamps.
Return all structural identity errors together before sample-size and pairwise heuristic checks.

Direct quality-engine callers may omit both bounds when no acquisition request exists. Empty input
continues to emit only `insufficient_data`. This decision does not define API validation for an
ill-formed request interval; it enforces the adapter's returned-evidence contract.

## Consequences

- Every successfully ingested bar is proven to belong to the exact half-open request that produced
  its quality report.
- Inclusive-end, pre-start, pagination, and timezone-boundary adapter defects become auditable
  failures rather than hidden cache pollution.
- No bar is silently trimmed or rewritten, and no heuristic threshold changes.

## Reversal

Stop supplying request bounds and remove `range_mismatch`. That would again allow overfetched bars
to enter shared storage under a passing report and is not recommended.
