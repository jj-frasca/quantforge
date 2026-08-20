# ADR-049: Preserve gate-component attribution in power calibration

- **Status**: Accepted
- **Date**: 2026-08-20
- **Deciders**: Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Extends**: ADR-041/042/045 (power, horizon, capture calibration)
- **Finding**: `docs/findings/FINDING-005-power-calibration-hides-gate-failures.md`

## Context

After whole-search trial accounting, production refinement, and the 200-candidate cap became part
of the calibrated procedure, every fresh planted-edge cell reported 0/50 detections. Even the
strongest trending cell captured 77.4% of a median +3.92 oracle Sharpe in sample and still produced
no graduate. `run_search` retains the six component verdicts on `best_gate_result`, but
`measure_power` reduces all of them to the single composite `graduate is not None` bit.

Zero power is an important result, not permission to relax a threshold. It does, however, require
attribution before any defensible next experiment can be chosen.

## Decision

**Every power artifact records a `gate_pass_counts` mapping for the six existing gate components:**
`dsr`, `pbo`, `stability`, `mintrl`, `holdout`, and `beats_buy_and_hold`.

Each value is the number of successfully searched symbols whose finalist passed that component,
whether or not it passed the composite gate. The denominator is always `n_symbols`; unsearchable
frames remain in `errors` and are excluded exactly as before. Both power drivers print one compact
line of `passed/N` counts. Missing attribution on a legacy artifact is represented by an empty
mapping.

This is an artifact-schema and reporting change only. Search, finalist selection, DSR, PBO,
stability, MinTRL, holdout, beat-buy-and-hold, and universe-deflation behavior remain byte-for-byte
unchanged. Search identity therefore does not change, although new power runs are required to
populate the diagnostic.

## Alternatives considered

1. **Store free-form rejection reasons.** Rejected: strings are presentation, can change wording,
   and make stable aggregation difficult.
2. **Store one primary failure per symbol.** Rejected: gate components are conjunctive and one
   finalist can fail several; imposing an order would hide interacting mechanisms.
3. **Infer the cause from capture and detection.** Rejected: capture is selected in-sample Sharpe,
   while four other in-sample gates and two holdout gates remain independent.
4. **Change the DSR dispersion estimator immediately.** Rejected without attribution across the
   full sweep. That would alter validation methodology in response to an empty funnel before the
   failure mechanism is measured.

## Consequences

- A zero-power run becomes a gate diagnostic instead of an opaque endpoint.
- Old power JSON remains valid but cannot claim component attribution.
- Re-running the two cloud workflows is compute-only and does not touch generated research-pool
  data or any validation threshold.

## Measured result, 2026-08-20

Runs 32341906980 and 32341908789 populated the diagnostic at N = 50 per cell. DSR passed **zero**
finalists in every cell. The strongest AR(1) trend cell is the cleanest attribution: at phi +0.30,
DSR passed 0/50, PBO 43/50, stability 40/50, and MinTRL/holdout/beat-buy-and-hold each 50/50. DSR is
therefore sufficient by itself to explain zero composite power at median oracle Sharpe +3.92.

The horizon cells also have DSR 0/50 throughout; their other pass counts vary with effect size and
horizon as expected. FINDING-006 records the newly isolated defect in the DSR dispersion estimator.

## Reversal

Remove `gate_pass_counts` and the two report lines. No search or gate behavior needs reverting.
