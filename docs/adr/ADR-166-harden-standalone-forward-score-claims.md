# ADR-166: Harden standalone forward-score claims

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Codex autonomous session 28 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-097
- **Extends:** ADR-023, ADR-025, ADR-148, ADR-149, and ADR-164

## Context

Paper and cross-sectional position boundaries protect attached forward scores, but their standalone
score and equity-point models remain shallowly frozen and under-validated. Direct computed results
can mutate before attachment, and unchecked copies bypass field validation at normal attachment.

## Options Considered

1. **Validate and freeze intrinsic evidence at the standalone roots.**
   - Pro: direct construction, explicit instance validation, JSON reload, and nested attachment
     share the same score/point contract.
   - Con: reconstructs small nested evidence and moves some rejection earlier than positions.
2. **Continue relying exclusively on positions.**
   - Pro: preserves permissive independent model behavior.
   - Con: leaves independent derived results mutable and malformed until eventual attachment.
3. **Replace scores with position-specific models.**
   - Pro: makes attachment identity structural.
   - Con: disrupts pure score producers and duplicates score fields.

## Decision

Always revalidate instantiated forward scores and points. Points require finite positive equity
and aware timestamps normalized to UTC. Both score roots require finite statistics, nonnegative
bar counts, aware UTC `as_of`, and defensive immutable JSON-shaped curve lists. Single-name trade
counts must be nonnegative and no greater than bars. Nonempty curves retain the existing length,
strict chronological order, and terminal-return relationships, and cannot extend after `as_of`.
Present cross-sectional evidence must be nonempty, have unique normalized symbols, and share one
executed revision; freeze its ordered list. Position boundaries continue to bind freeze dates and
symbol/universe identity. Keep empty legacy curves, absent evidence, and historical beats flags.

## Consequences

- Standalone derived evidence cannot drift by ordinary list mutation.
- Unchecked copies are rejected on explicit validation and nested attachment; `model_copy` itself
  remains Pydantic's intentionally unchecked API.
- Existing persisted JSON arrays/objects and legacy unmeasured states remain supported. No formula,
  quality rule, financial estimator, lifecycle predicate, gate, or threshold changes.
- Input errors surface earlier, before an enclosing position is required.

## Reversal

Restore permissive standalone roots. That reopens FINDING-097 and is not recommended.
