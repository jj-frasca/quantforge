# ADR-167: Validate the research dataset frame contract

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Codex autonomous session 28 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-098
- **Extends:** ADR-004, ADR-119, ADR-137, ADR-164, and ADR-165

## Context

Canonical acquisition checks PriceBars, but direct `ResearchDataset` construction and replacement
only validate evidence and calendar structure. A passed report can accompany missing/invalid price
columns or observations outside its requested interval. Consumers trust the dataset boundary.

## Options Considered

1. **Validate the intrinsic canonical numeric frame at dataset capture.**
   - Pro: all direct and acquisition callers share structural price/range rules; invalid inputs
     fail before discovery or forward scoring.
   - Con: adds a linear frame scan and rejects unsupported object-valued feature columns.
2. **Reconstruct full PriceBars and rerun quality heuristics from a frame.**
   - Pro: also reruns heuristics.
   - Con: frames omit source/adjustment evidence, so reconstructing it would invent provenance.
3. **Validate only consumers.**
   - Pro: avoids dataset changes.
   - Con: inconsistent repeated guards and future consumers can miss them.

## Decision

Validate the retained frame snapshot before exposing it. Require unique flat columns including `close`,
real numeric nonboolean column dtypes, and finite values. Present OHLC columns must be positive and
obey low/high bounds against other present OHLC columns. Present volume must be nonnegative.
Every timestamp must lie in the evidence's half-open `[start, end)` range. Retain the existing
nonempty, aware, unique, ascending calendar checks. Preserve close-only synthetic frames and
aware offset calendars; canonical production acquisition already provides numeric OHLCV.

## Consequences

- Missing/nonfinite/malformed prices and out-of-range frames fail at direct construction or
  dataclass replacement, before search/forward consumers use them.
- Arbitrary object-valued cells are now explicitly rejected at this canonical numeric boundary,
  closing ADR-165's unsupported object-payload ownership surface.
- No prices are repaired, filled, clipped, or renormalized. Heuristic quality rules and validation
  thresholds do not change. No generated JSON schema or record changes.
- Intrinsic validity still cannot prove a supplied report was computed from the supplied values;
  production callers must continue through `prepare_research_dataset` on checked PriceBars.

## Reversal

Remove the intrinsic frame guards. That reopens FINDING-098 and is not recommended.
