# ADR-250: Revalidate cross-sectional experiment before promotion

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 35, ISO 2026-W41
- **Resolves:** FINDING-199
- **Extends:** ADR-145, ADR-149
- **Relates to:** ADR-024, ADR-025, ADR-142, ADR-249

## Context

The cross-sectional freeze projection reads the graduate and frozen inputs without
revalidating the originating experiment. Unchecked copies can contradict the
selected trial or passing gate yet produce a valid CrossSectionalPosition. The
position omits those source records, so its own validation cannot recover the
discarded relationships. ADR-249 closes the analogous single-name boundary.

## Options Considered

1. Reconstruct the complete experiment at promotion entry.
   - Pro: reuses authoritative source contracts before information is discarded.
   - Con: incurs one complete reconstruction per promotion attempt.
2. Trust store validation and caller provenance.
   - Pro: no additional projection work.
   - Con: leaves public in-memory unchecked copies outside the source boundary.
3. Duplicate source selection and gate rules in the position.
   - Pro: apparent local protection.
   - Con: the position lacks source trials and lineage; duplicate rules drift.

## Decision

At freeze_cross_sectional_graduate entry reconstruct through
CrossSectionalExperiment.model_validate(experiment.model_dump(round_trip=True)).
Then retain the original absent-graduate refusal, required fundamental-snapshot
refusals and position construction. Use all existing authoritative source rules
without adding a new selected-trial, gate, lineage or snapshot policy.

Preserve legacy absent lineage and structured holdout, exact universe order,
None/partial/empty score snapshots, original cost and freeze timestamp, and
price-only legacy eligibility. Manager preselection and other forward consumers
remain separate; its existing ValueError catch still skips invalid promotion.
No estimator, factor, threshold, durable schema, broker action or generated data
changes. No cohort or workflow rerun.

## Consequences and reversal

An unchecked source cannot turn invalid graduation evidence into a forward claim
by discarding its trials and gate. Promotions pay one reconstruction cost, and
future source-contract changes apply at this boundary automatically. Tests must
prove invalid-source refusal before output plus exact valid-position preservation.
Remove only entry reconstruction to reverse this correction and reopen FINDING-199.
