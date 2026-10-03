# FINDING-087: Fundamental-pool claims are shallow and unvalidated

- **Severity:** High — mutable or unchecked records can silently change factor inputs in durable evidence
- **Status:** Resolved by ADR-155
- **Date:** 2026-10-03
- **Affects:** ADR-029 fundamental discovery and consolidation

## Finding

`FundamentalRecord` is declared frozen, but its `flags` list remains mutable. A caller can append,
remove, or replace diagnostic meaning in place and later serialize a different durable claim under
the same company/filing identity. Pydantic also accepts non-finite score values; JSON serialization
turns `NaN` and infinity into `null`, so the written record no longer round-trips and can silently
drop a company from quality, value, or combined factor maps.

The model does not enforce the score relationships the ADR-029 producer assumes: quality, value,
and combined scores must be finite in `[0, 1]`; F-score must be in `[0, 9]`; and a present combined
score must equal quality multiplied by value, while remaining absent unless both legs exist.
Finally, `merge_fundamental_records` and the consolidation writer trust already-instantiated models,
so `model_copy(update=...)` can bypass any model rule and reach `fundamentals_pool.json`.

A read-only audit found all 4,244 committed rows already satisfy these relationships and have unique
CIKs. No generated-data migration is required.

## Required correction

Make the complete `FundamentalRecord` the authoritative claim boundary: defensively freeze flags
while preserving their JSON array shape, reject non-finite or out-of-range scores, validate the
combined-score relationship, and revalidate all existing and incoming records before merge output
can reach consolidation. Invalid input must fail before the canonical pool file is touched. Preserve
newest-filing deduplication, SIC fields, rankings, factor formulas, generated data, and every
validation threshold.
