# ADR-218: Validate power-calibration root claims

- **Status:** Accepted
- **Date:** 2026-10-08
- **Deciders:** Codex autonomous session 19, ISO 2026-W41
- **Resolves:** FINDING-167
- **Extends:** ADR-041, ADR-053, ADR-158, ADR-215

## Context

Deep immutability does not validate the power denominator, counts, rate or
universe bar. The root accepts invalid original types, nonfinite summaries and
contradictory counts/rates; authoritative sweep reconstruction retains them.

## Decision

Apply the established null-root contracts to corresponding power claims:
original positive nonboolean integral searched symbols; original nonnegative
nonboolean integral detected/survivor counts; original finite real nonboolean
rate in [0,1]; and an original finite real nonboolean nonnegative deflation bar.
Require survivors <= detected <= searched and rate exactly detected/searched.
Reuse existing guards without clamping, inferring or dropping evidence.

Preserve signed process/reference scores, all legacy optional arrays, JSON
shapes, valid numeric scalars and original range checks before float rounding.
Sweep reconstruction inherits the root guards. This does not add array lengths,
reference/process-parameter contracts, component-count relationships, bar-formula
recomputation or joint-verdict recounting. No search, reference strategy, gate,
threshold, calibration identity, workflow or generated-data changes.

## Alternatives and limits

Checking only serialization leaves standalone claims and inference unsafe.
Permitting approximate rates admits contradictions despite an exact producer
ratio. Repairing invalid values silently substitutes a different experiment.
Broader power evidence validation needs separate reproduced findings.

## Verification

Observe original scalar/count/rate and unchecked-copy sweep failures first.
Protect zero/all detections, equal count boundaries, supported numpy/Fraction
values, empty legacy arrays and Hypothesis coherent count-ratio round-trips.
Read all committed power cells without writes; independently review and run
focused consumers plus the full foreground gate before delivery.

## Reversal

Remove the root validators and count/rate checks. This reopens FINDING-167
without changing valid power-calibration arithmetic.
