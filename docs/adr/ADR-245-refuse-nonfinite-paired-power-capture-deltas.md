# ADR-245: Refuse nonfinite paired power capture deltas

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 33, ISO 2026-W41
- **Resolves:** FINDING-194
- **Extends:** ADR-057, ADR-243
- **Relates to:** ADR-045, ADR-055, ADR-218, ADR-219

## Context

Finite gross/net capture endpoints do not imply finite native subtraction.
compare_power_sweeps accepts opposite-sign endpoints of magnitude 1e308 and
publishes infinite deltas. Default JSON renders these as null, also used for
unmeasured comparisons. Finalist movement can still mark that row attributable.
This synthetic downstream arithmetic defect does not revise production capture
or calibration rates and is separate from ADR-243's endpoint guards.

## Options Considered

1. Refuse a nonfinite native subtraction result. Preserves the existing finite
   arithmetic and distinguishes an invalid comparison from unmeasured evidence.
2. Convert invalid differences to None. Conflates arithmetic failure with the
   existing unmatched/legacy refusal and can retain attributable=True.
3. Clamp or replace the estimator/serialization. Changes the measured result or
   its public representation instead of enforcing the local arithmetic boundary.

## Decision

After _delta's existing None early return, execute the original after-before
subtraction and require a finite result, raising ValueError otherwise. Preserve
finite native differences exactly, including signed zero and finite underflow.
No fallback, clamp, stable-arithmetic recovery or invalid-to-None conversion.

Do not change unmatched-cell behavior, eligibility, finalist attribution, noise
refusals, detection differences, reference estimator or serialization defaults.
Direct construction of PowerSweepComparison remains outside this producer guard.
No thresholds, source laws, search/gate versions or generated artifacts change.

## Verification and reversal

Observe both signs of overflow through public matched comparisons before code;
exercise gross and net differences independently. Verify exact finite native
subtraction, None and unmatched behavior, signed zero and property cases.
Independently review and run the full foreground gate before delivery.
Removing the result guard reopens FINDING-194.
