# ADR-257: Disclose column-order tie handling

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 35, ISO 2026-W41
- **Resolves:** FINDING-206's documentation claim
- **Relates to:** ADR-024, ADR-025, ADR-140, ADR-149, ADR-252

## Context

long_short_weights uses rank(method="first") but its docstring and a test comment
claim that tie selection is independent of column order. Repeated fixed-order
inputs are deterministic; permuting tied symbols can change the chosen legs.
The frozen ordered universe already preserves that reconstruction identity.

## Options Considered

1. Qualify the source-facing claim and record the actual behavior.
   - Pro: corrects documentation without altering frozen factor semantics.
   - Con: leaves the existing column-order tie convention in place.
2. Change tie handling to average ranks, sorting or another allocation.
   - Pro: could implement a different invariance convention.
   - Con: changes selected names, turnover and returns without a method decision.
3. Leave the incorrect guarantee.
   - Pro: no edits.
   - Con: readers may treat a repeatability test as proof of permutation invariance.

## Decision

State that ties follow supplied column order and selection is deterministic for a
fixed ordered panel, while reordering tied symbols may change the selected names.
Correct the misleading test comment without changing assertions. Record the toy
counterexample and explain the ordered-universe relationship in cold memory.
Keep the complete executable ranker and test AST unchanged except documentation.

## Consequences and reversal

Documentation describes the method actually used by historical and frozen factors.
This is a wording qualification, not a new tie policy or estimator. No new runtime
behavior is implemented, so do not fabricate a RED test or add wording-matching
tests; verify published executable/test AST identity and run existing gates instead.
An actual tie-method change needs a separate methodology ADR and appropriate
identity/validation evidence. Existing calibration or forward claims are not relabeled.
Restoring the old wording would reopen FINDING-206's false invariance guarantee.
