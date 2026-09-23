# ADR-118: Bind quality evidence to a unique calendar and adapter source

- **Status:** Accepted
- **Date:** 2026-09-23
- **Deciders:** Codex autonomous session 10 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-046
- **Extends:** ADR-006 and ADR-115

## Context

`DataQualityEngine.check` sorts canonical bars and verifies their symbols, but it neither rejects
duplicate timestamps nor verifies their source against the adapter used by `DataIngestionPipeline`.
Both omissions break the assumption that one report describes one time series. Production storage
uses `(symbol, timestamp_utc, source)` as its primary key: same-source duplicates are silently
upserted, while different sources coexist and are both returned because reads do not select a
vendor. The in-memory repository retains every duplicate. A passing report can therefore be
followed by repository-dependent evidence.

## Options Considered

1. **Reject duplicate timestamps and adapter-source mismatches at the quality boundary.**
   - Pro: fails before pairwise heuristics and storage; gives every passing report one unambiguous
     calendar and producer; keeps repository behavior irrelevant to evidence identity.
   - Con: a vendor duplicate that could be deterministically collapsed blocks ingestion until the
     adapter is corrected.
2. **Deduplicate in the normalizer or repository.**
   - Pro: produces a usable series without failing the request.
   - Con: choosing first, last, or an aggregate silently invents a vendor-resolution policy; the
     production and in-memory repositories already disagree, and a report would not record which
     observation survived.
3. **Permit mixed sources and add `source` to every read filter.**
   - Pro: preserves multiple vendors for future cross-validation.
   - Con: ingestion currently requests one adapter at a time, while ADR-006 check #8 requires an
     explicit vendor-comparison design. Accidental mixing is not cross-validation and must not be
     treated as such.

## Decision

Extend `DataQualityEngine.check` with an optional expected source. For any non-empty input, run a
single structural-identity preflight before sample-size or time-series checks:

- the bar-symbol set must equal the normalized requested symbol (ADR-115);
- `timestamp_utc` must be unique across the series;
- the bar-source set must contain exactly one source and, when the pipeline supplies an expected
  source, it must equal that adapter source.

Emit `duplicate_timestamp` and `source_mismatch` errors as applicable, alongside
`symbol_mismatch` when multiple structural dimensions fail, then return without pairwise
heuristics. `DataIngestionPipeline` supplies `adapter.source`. Direct quality-engine callers may
omit the expected source, but mixed sources still fail. Empty input continues to emit only
`insufficient_data`. No warning threshold or vendor-cross-validation behavior changes.

## Consequences

- A passing report describes one symbol, one vendor, and one observation per timestamp.
- Same-source duplicates no longer depend on production upsert order or differ from in-memory
  behavior; mixed vendors cannot create duplicate research rows through an ordinary ingestion.
- The pipeline persists structural failures and stores no bars, preserving ADR-006's auditable
  fail-soft behavior.
- Future vendor cross-validation remains a separate multi-series operation rather than an implicit
  mixed list passed through single-series heuristics.

## Reversal

Remove the two structural checks and stop passing the adapter source. This would restore ambiguous,
repository-dependent evidence and is not recommended.
