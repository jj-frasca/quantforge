# ADR-047: Calibrate the same adaptive refinement production searches

- **Status**: Accepted
- **Date**: 2026-08-19
- **Deciders**: Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Extends**: ADR-036/037/041/042 (calibration), ADR-044 (search identity), ADR-046 (trial accounting)
- **Finding**: `docs/findings/FINDING-004-calibration-omits-production-refinement.md`

## Context

Production discovery resolves every coarse family grid, chooses the coarse winner, and performs a
second grid search centered on that winner (`refine=True`, `refine_span=0.25`). Null and power
calibration stop after the coarse pass. The adaptive pass changes both the hypotheses and the
selection procedure, but the calibration fingerprint does not include its policy.

The scheduled calibration numbers must be refreshed anyway because ADR-046 changed DSR/MinTRL
trial accounting and deliberately changed calibration identity. Fixing refinement parity before
that refresh avoids spending cloud compute on a second known-incomplete procedure.

## Decision

**Null and power calibration default to production's coarse-to-fine search:** `refine=True` and
`refine_span=0.25`.

- `calibrate_gate` and `measure_power` accept explicit refinement arguments and pass them unchanged
  to every `run_search` call.
- `calibration_search_version` hashes `refine` and `refine_span` alongside the coarse grids. The
  refined concrete grid is data-dependent because its center is the coarse winner; the deterministic
  algorithm inputs are the stable procedure identity.
- `NullCalibration` and `PowerCalibration` expose the two fields with legacy-safe defaults. New
  artifacts say which selector they measured without requiring a reader to reverse an opaque hash.
- CLI drivers use the production defaults. A future coarse-only diagnostic must pass
  `refine=False` explicitly and receives a different fingerprint.

No gate threshold, strategy grid bound, null generator, planted edge, or generated data file is
changed locally. Scheduled workflow sole writers will replace stale artifacts on their next run.

## Alternatives considered

1. **Disable refinement in production.** It would restore parity and reduce adaptive search, but it
   deletes an ADR-014 search stage rather than calibrating it. No evidence says the stage is useless.
2. **Keep coarse calibration and label it an optimistic lower bound.** Honest wording, but it leaves
   the production composite Type-I error unknown when the existing harness can measure it directly.
3. **Fingerprint only `refine=True`.** Insufficient: changing the span changes the concrete local
   hypotheses while leaving the boolean unchanged.

## Consequences

- The next null/power runs measure the selector production actually deploys.
- Calibration cost rises by one winner-family grid per symbol; it does not repeat the full catalog.
- Published coarse-only numbers remain historical evidence for that procedure but are stale for
  production and distinguishable by search identity.

## Reversal

Restore coarse-only calibration defaults, remove refinement fields from artifacts and identity, and
accept that calibration no longer measures production discovery.
