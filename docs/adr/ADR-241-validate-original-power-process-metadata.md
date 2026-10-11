# ADR-241: Validate original power process metadata

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 31, ISO 2026-W41
- **Resolves:** FINDING-190
- **Extends:** ADR-158, ADR-218, ADR-219, ADR-220

## Context

PowerCalibration records the planted process through optional phi, half_life and
deviation_share. Plain float fields accept original booleans and numeric strings,
coerce them into numbers, and retain NaN and infinity. Sweep reconstruction
therefore also accepts invalid provenance and nonfinite ordering metadata.
Independent review reproduced all three fields and checked all 12 committed cells.

## Options Considered

1. Validate the original optional scalar using the established finite leaf guard.
2. Rely on float coercion or derived sweep checks. Original evidence disappears.
3. Add generator ranges or process-family completeness constraints. These change
   the descriptive legacy contract and require separate scope.

## Decision

Add one before field validator for phi, half_life and deviation_share. Preserve
None and absent defaults; otherwise return _finite_leaf_score(value), requiring
original finite float-representable real nonboolean evidence. Keep existing float
normalization and all finite signed/zero/out-of-generator-domain metadata values.
Authoritative sweep reconstruction already rebuilds cells and needs no change.

This validates scalar evidence, not process-law completeness or generator-domain
correctness. No field, schema default, source, reference, procedure, fingerprint,
threshold or generated artifact change. FINDING-155 and FINDING-159 remain Open.

## Verification

Before code, exercise direct construction, JSON and unchecked-copy sweep
reconstruction for all three fields. Protect None/absence, numeric normalization,
broad finite domains and ordinary serialization. Independent read-only audit of
all 12 committed cells, affected tests, full foreground make check-all and exact
master CI are required before completion.

## Consequences and reversal

Malformed scalar provenance cannot become accepted power metadata through float
coercion or sweep reconstruction. Removing the validator reopens FINDING-190.
No historical outcome or process-law claim is restated.
