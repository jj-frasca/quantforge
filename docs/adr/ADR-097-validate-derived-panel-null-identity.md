# ADR-097: Validate every derived panel-null identity

- **Status:** Accepted
- **Date:** 2026-09-21
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Acts on:** FINDING-029
- **Extends:** ADR-081, ADR-083, ADR-090

## Context

Each null replicate already receives a deterministic SHA-256 `panel_id` derived from the complete
frozen cohort serialization and its global panel index. That field is persisted through scratch
shards and the final calibration, but current artifact validation checks only that IDs are unique.
Unlike the seed, it does not prove that the stored ID is the value prescribed by the cohort/index
contract.

The measurement is unspent, so the artifact boundary can be made exact without compatibility or
migration concerns.

## Decision

Expose one deterministic `panel_identity(cohort, panel_index)` primitive. It validates the cohort
and index range, then returns the existing SHA-256 derivation. Replicate execution uses this
primitive when emitting a panel. Shard and final-calibration validation re-derive and require the
same value for every replicate.

No seed, panel draw, search, diagnostic, inference input, gate, or validation threshold changes.

## Consequences

- A persisted replicate cannot substitute an arbitrary unique ID.
- An ID derived from another cohort or global index fails at load/consolidation.
- Execution and validation cannot drift between duplicate-only and derived-identity semantics.
- Existing synthetic tests must construct IDs from their test cohort rather than opaque labels.

## Reversal

Removing derived-ID validation requires an explicit decision that `panel_id` is merely an
untrusted display label; retaining it as an identity while accepting arbitrary values would restore
FINDING-029.
