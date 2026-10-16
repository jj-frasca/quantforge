# ADR-299: Bind persisted trial counters to recorded evaluations

- **Status:** Accepted
- **Date:** 2026-10-16
- **Deciders:** Codex autonomous session 21, ISO 2026-W42
- **Resolves:** FINDING-253
- **Extends:** ADR-046/062/066/145/147/150/162/295

## Context

Both experiment models accept lifetime_trials=1 with one trial explicitly recording
four evaluated configurations. JSON reload and memory stores retain that claim;
the next four-configuration search can receive prior1 and compute lifetime5 rather
than at least8. Other larger stored counters can mask the bad record. These are
synthetic model/store counterexamples, not observed production undercount or a
false graduate. Original booleans and integer-valued float/Fraction counters also
coerce into integers; truly fractional values already reject without truncation.

A fresh read-only audit at 0c7d4731 found all 3,318 committed experiments compatible
with original integral domains and the local lower bound. There are 157 missing
legacy trial counts, whose existing default1 remains an honest lower bound; no
historical evaluated count may be inferred from today's catalog. All 608 source
JSON files were byte-preserved. See FINDING-253 for exact audit identities.

## Options considered

1. Validate original counter domains and local coherence on canonical models:
   prevents contradictory recorded counts without rewriting historical evidence;
   adds explicit refusals and model-validation work.
2. Trust search producers and validate only future prior arguments: simpler,
   but an understated positive prior survives ADR-295 and prices fewer hypotheses.
3. Infer or repair counts from catalog grids or retained history: could invent
   precise-looking totals, violates generated-record ownership and ignores pruning.
4. Change store max aggregation to sum or timestamp ordering: does not repair
   individual claims and reintroduces historical double counting or reset issues.

## Decision

Reuse require_trial_count for before-coercion field validation. Trial requires
original positive nonboolean Integral n_evaluated_configs; CrossSectionalTrial
inherits this contract. Missing legacy values keep default1. Both experiment
models require original nonnegative nonboolean Integral lifetime_trials. Normalize
accepted integral scalars to Python int before Pydantic storage and summation.

Add a separate after-model validator, registered after existing lineage checks,
requiring lifetime_trials >= sum(trial.n_evaluated_configs). Preserve larger
cumulative priors, empty-trial zero counters, existing lineage ordering for valid
counter sources, fields, default values and JSON shapes. This is only a local
lower bound, not equality, timestamp monotonicity or reconstruction of all prior
searches. Current search count recipes and max-based store/report aggregation stay.

Both memory stores reconstruct incoming model dumps through their canonical
experiment model before append, matching existing JSON-writer validation. Reject
unchecked copies without changing current contents. Store an equal validated
snapshot, retaining UUID/time/content rather than caller object identity; accept
the additional bounded model-graph validation cost. Existing JSON writers inherit
the new model guards before filesystem access; do not alter their I/O or retention.

No estimator, gate predicate, threshold, search/accounting-v14 fingerprint,
calibration procedure, historical record or generated-file change. No migration
is needed by the measured compatibility audit, and no hidden historical count is
asserted. Holdout-score and scalar-projection findings remain separate.

## Consequences, verification and reversal

Canonical persisted counts cannot contradict their own recorded evaluations,
and unchecked memory additions cannot poison a future prior. TDD must observe
constructor/reload/type/undercount failures first, then cover inherited trial
guards, default1, empty0, large integral normalization, higher priors, invalid
unchecked additions and unchanged store contents/files. Hypothesis verifies
local accounting bounds. Repeat the read-only actual-model compatibility audit;
run independent review and foreground make check-all before individual delivery.

Remove the counter validators and restore memory append behavior to reverse,
reopening FINDING-253. Preserve its evidence and all generated records.
