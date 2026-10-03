# ADR-155: Harden fundamental-pool claims

- **Status:** Accepted
- **Date:** 2026-10-03
- **Deciders:** Codex autonomous session 22 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-087
- **Extends:** ADR-029, ADR-095, ADR-129, ADR-146, and ADR-150

## Context

ADR-145 through ADR-150 established deep immutable boundaries and store-side revalidation for
strategy experiments and forward positions. The independent ADR-029 fundamentals pool still trusts
a shallowly frozen record: its flags mutate in place, score scalars accept non-finite values, and
the merger/consolidator can serialize validation-bypassing model copies. Those fields directly feed
the `xs_quality`, `xs_value`, and `xs_quality_value` factor inputs.

All 4,244 committed rows already satisfy the proposed finite, range, composite, and unique-CIK
relationships, so hardening the boundary requires no generated-data rewrite.

## Options Considered

1. **Validate and deep-freeze at `FundamentalRecord`, then revalidate at merge.**
   - Pro: construction, JSON load, ranking, and durable consolidation share one claim definition.
   - Con: adds one reconstruction per input row during a weekly consolidation.
2. **Validate only in `compute_fundamental_record`.**
   - Pro: keeps the model permissive.
   - Con: persisted shards and unchecked model copies remain hostile inputs; producer trust is not a
     durable boundary.
3. **Validate only in the consolidation script.**
   - Pro: protects the canonical file.
   - Con: direct consumers can still observe mutable or incoherent records, and validation logic
     would drift away from the model used to load the pool.

## Decision

Make `FundamentalRecord` the complete claim boundary. Store flags as a defensive immutable sequence
and serialize them as the existing JSON array. Require quality, value, and combined scores to be
finite and in `[0, 1]`; require F-score in `[0, 9]`; require gross profitability to be finite when
present; and require `combined_score == quality_score * value_score` within floating-point
tolerance exactly when both component scores exist.

`merge_fundamental_records` reconstructs every existing and incoming record through
`FundamentalRecord.model_validate(model_dump(round_trip=True))` before deduplication. This closes
Pydantic's unchecked-copy bypass before consolidation creates or rewrites the canonical file while
keeping ADR-129's corrupt-shard handling and ADR-029's newest-filing merge semantics unchanged.

## Consequences

- Factor score inputs cannot drift through nested mutation or non-round-trippable numeric values.
- Construction, pool/shard load, merge, and durable consolidation enforce one record definition.
- Existing JSON keeps its array/object shape and all committed rows remain readable unchanged.
- No factor formula, score threshold, SIC field, generated record, or workflow schedule changes.

## Reversal

Restore mutable flags or trust incoming model instances during merge. That would reopen
FINDING-087 and is not recommended.
