# ADR-249: Revalidate experiment before paper promotion

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 33, ISO 2026-W41
- **Resolves:** FINDING-198
- **Extends:** ADR-147, ADR-148
- **Relates to:** ADR-019, ADR-020, ADR-033, ADR-079

## Context

freeze_graduate reads an Experiment's graduate directly. Unchecked model copies
can violate the authoritative selected-trial, graduate and gate relationships yet
become valid PaperPosition objects. That narrower projection omits trial/gate
records, so downstream position validation cannot recover discarded source evidence.
Ordinary validated stores are protected; the public in-memory projection is not.

## Options Considered

1. Reconstruct the complete Experiment at projection entry using its round-trip
   dump. Reuses all existing source rules without duplicating or changing them.
2. Trust caller validation. Unchecked copies bypass constructor provenance.
3. Reimplement graduation checks in PaperPosition. The projected record lacks
   source evidence and duplicate rules would drift from Experiment validation.

## Decision

At freeze_graduate entry reconstruct with
Experiment.model_validate(experiment.model_dump(round_trip=True)), before reading
or discarding source fields. Then keep the original absent-graduate refusal,
universe-deflation calculation and PaperPosition construction unchanged.

Preserve authoritative legacy selected-index fallback, optional manifest/quality
and structured-holdout absence. ADR-033 remains descriptive: failing universe
deflation is recorded and still paper eligible, while a failed graduation gate
remains ineligible under existing Experiment/Graduate rules. No new thresholds,
parameter domains, source criteria, schema or broker actions are introduced.
Manager preselection, independent forward/lifecycle consumers and source-store
policy remain separate. No real cohort, artifact or workflow rerun.

## Verification and reversal

Observe unchecked source copies failing promotion before code: selected identity,
graduate parameters/strategy, gate contradiction and fundamental/distress vetoes.
Require source refusal before deflation/output construction; preserve exact valid
modern/legacy positions, absent graduate behavior and caller nonmutation.
Independently review and run the full foreground gate before delivery.
Removing reconstruction reopens FINDING-198 at the projection boundary.
