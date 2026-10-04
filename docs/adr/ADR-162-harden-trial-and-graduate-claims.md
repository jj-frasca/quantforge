# ADR-162: Harden standalone trial and graduate claims

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Codex autonomous session 27 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-093
- **Extends:** ADR-014, ADR-016, ADR-046, ADR-054, ADR-104, ADR-147, and ADR-160

## Context

ADR-147 made the complete single-name experiment graph defensive, but deliberately left the shared
`Trial` and `Graduate` models unchanged outside that boundary. Both remain shallowly frozen and
accept invalid or contradictory methodology evidence at direct construction. Search repricing also
uses Pydantic's validation-bypassing `model_copy(update=...)` before winner selection and durable
attachment.

The defect is observable without changing any methodology: non-finite fields serialize as JSON
`null`, public parameter mutation changes strategy identity, and a `Graduate` can name a failed
gate or disagree with the gate's structured holdout evidence. All committed records already meet
the stronger invariants, so the correction does not require a generated-data migration.

## Decision

Harden the shared leaf models themselves while preserving their existing JSON shapes.

`Trial` will defensively copy parameters into an immutable JSON-object-compatible mapping, require
a non-empty strategy name and finite numeric parameters/statistics, constrain PBO and parameter
stability to `[0, 1]`, and constrain nullable probability-form DSR to `[0, 1]`. Nullable
walk-forward and purged-CV values remain honestly unmeasured when absent and must be finite when
present. Candidate-count semantics remain `n_evaluated_configs >= 1`.

`Graduate` will apply the same strategy/parameter boundary, require a passing internally coherent
`GateResult`, finite holdout Sharpe and total return, positive holdout length, wealth-preserving
total return greater than `-1`, and equality with the gate's structured holdout values when those
legacy-nullable fields are present. The nested gate will be reconstructed before these checks.

Both longitudinal and cross-sectional search repricing will reconstruct the concrete trial subtype
through validation rather than use unchecked model copies. This decision changes no statistic,
selection rule, gate predicate, threshold, candidate budget, workflow, or generated data.

## Alternatives considered

1. **Rely on ADR-145/147 outer experiment validation.** Rejected: invalid leaves exist and are used
   before attachment, and future direct consumers should not need to reproduce every leaf rule.
2. **Freeze parameter mappings only.** Rejected: non-finite and contradictory evidence would still
   serialize as a different claim or misstate graduation.
3. **Replace persisted fields with computed properties.** Rejected: that would change the durable
   schema and make historical payload compatibility needlessly difficult.

## Consequences

- A trial or graduate cannot drift after construction or carry evidence outside its stated domain.
- Search winner selection operates only on revalidated repriced trials.
- Existing experiment JSON shapes and all committed records remain compatible.
- Legacy gate results may still omit both structured holdout fields; when present, they must agree
  with the graduate exactly.

## Reversal

Restore mutable parameter dictionaries, independent scalar acceptance, or unchecked repricing.
That reopens FINDING-093 and is not recommended.
