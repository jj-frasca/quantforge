# ADR-159: Harden validation result claims

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Codex autonomous session 26 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-091
- **Extends:** ADR-038, ADR-039, ADR-078, and ADR-158

## Context

`ValidationReport` is the MVP methodology claim and the input to StrategyLab's gate. Its nested
walk-forward, purged-CV, interpretation, flag, and regime containers remain mutable despite
`frozen=True`. The result models also accept non-finite statistics and contradictory counts or
summaries, while unchecked Pydantic copies bypass construction validation. Accepted NaN/infinity
becomes JSON `null`, so the serialized claim can differ from the in-memory verdict.

## Decision

At construction, defensively reconstruct and freeze the complete validation result graph while
preserving its existing JSON arrays and objects. Require finite scalar evidence; non-negative or
positive counts as appropriate; unit-interval consistency; exact split/fold counts; and summaries
that agree with their nested records. When a diagnostic is present, its count must agree with the
corresponding top-level report count.

The gate and API response boundary reconstruct incoming reports through the authoritative model
before interpreting or returning them. An unchecked copy therefore fails before a verdict or
external claim is emitted. This decision changes no split geometry, estimator, search, diagnostic,
pass formula, threshold, workflow, or generated data.

## Alternatives considered

1. **Freeze containers only.** Rejected: contradictory and non-finite evidence would remain valid.
2. **Validate only evaluator outputs.** Rejected: JSON reload and direct construction are public
   model boundaries, and unchecked copies can bypass the evaluator.
3. **Rely on JSON round trips before use.** Rejected: the API and gate consume live model objects;
   non-finite values already lose information during serialization.

## Consequences

- One validation claim cannot drift after construction under the same headline and pass verdict.
- Direct and deserialized result graphs fail closed on invalid or contradictory evidence.
- Existing JSON shapes and valid computed values remain backward compatible.
- Gate and API consumers reject hostile validation-bypassing copies.

## Reversal

Restore mutable result containers or trust instantiated reports at consumers. That reopens
FINDING-091.
