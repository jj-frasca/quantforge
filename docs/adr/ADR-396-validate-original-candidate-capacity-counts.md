# ADR-396: Validate original candidate-capacity counts

- **Status:** Accepted
- **Date:** 2026-10-28
- **Deciders:** Codex autonomous session12, ISO2026-W44
- **Addresses:** FINDING-333 within generic candidate-count boundaries
- **Extends:** ADR-048/295

## Context

Malformed fractional direct counts can overspend their supplied selector limit
or allocation budget; empty paths can conceal invalid counts. Independent
research reproduced limit1.5 selecting two and budget2.5 allocating five. No
ordinary production occurrence is established: GateConfig supplies validated
integer budgets. Python annotations alone do not enforce discrete runtime counts.

## Options Considered

1. **Reuse original count validation (chosen).**
   - Pro: rejects ambiguous counts before arithmetic and preserves Integral
     interoperability by normalizing NumPy signed/unsigned scalars to Python int.
   - Con: formerly tolerated coercible direct inputs now refuse explicitly.
2. **Round/coerce counts or change while remaining to while remaining>0.**
   - Pro: avoids one runaway fractional-budget symptom.
   - Con: invents a count and leaves fractional limits, capacity and empty paths
     ambiguous; it does not enforce the declared domain.
3. **Validate catalog/grid settings at the same time.**
   - Pro: broader early input refusal.
   - Con: expands scope into independent n_per_param and parameter-vector policy.

## Decision

At select_space_filling_candidates entry, replace its weak negative-limit check
with require_trial_count(limit, minimum=0, parameter="limit") before len, shortcuts
or callbacks. At allocate_candidate_budget entry, validate/normalize budget first
and refinement_capacity second with the same helper/minimum, before sorting or
materializing families, eligibility and arithmetic. Require original nonboolean
numbers.Integral, returning Python int; do not coerce floats, Fractions, strings,
arrays or booleans. Errors name the count as a nonnegative nonboolean integer.

Keep zero, empty/ineligible families, eligible refinement-only capacity,
minimum-two rules, ordering, maximin calculations, water filling and all defaults.
Accept large integers without a new allocation cap. The catalog wrapper's earlier
grid construction and n_per_param domain remain separate. No statistical
threshold, search method identity, v14 or persisted/generated shape changes.

## Consequences and verification

Generic malformed counts refuse before any family/candidate inspection. The
negative-limit diagnostic migrates to the shared count wording; retain its
negative-input refusal test. Valid original integer outputs and fingerprints
must remain exact; no production overrun or historical repair is claimed.

Before source edits, freeze395 complete accepted-count selection/allocation/error
claims, five gate/search fingerprints and module AST. TDD malformed counts on
ordinary/empty/ineligible inputs, inspection/callback refusal and count precedence;
zero/minima/refinement-only/large Python and NumPy count controls; Hypothesis
accepted-count cap invariants. Replay the baseline and whole AST outside the
three guards, old negative-limit replacement and one import. Run independent
research review, existing search/budget regressions, foreground make check-all,
safe individual publication and exact CI. No provider/search/cohort measurement
or generated-data edit is required.

Reversal restores only the old weak limit check and removes the two allocator
entry checks/import. Retain F333 and this ADR as the record.
