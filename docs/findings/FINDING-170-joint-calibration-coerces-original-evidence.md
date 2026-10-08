# FINDING-170: Joint calibration coerces original evidence

- **Date:** 2026-10-08
- **Severity:** High — canonical calibration evidence validity
- **Status:** Resolved by ADR-220
- **Reproduced revision:** `8e216cc9`

CalibrationSymbolVerdict accepts boolean/string probabilities, boolean/string
holdout scores and boolean/float/string history counts when their coerced
values match legitimate incumbent projections. Exact Fraction probabilities
just above one or below zero become accepted one or negative zero because
field bounds run after conversion. Standalone joint records therefore retain
malformed original evidence that can feed candidate composite passage or
ADR-018 survival re-judgment after reconstruction.

Independent review reproduced nine malformed original cases. All 400 joint
records in eight committed null artifacts already satisfy the proposed original
contracts and holdout projections; the 12 committed power cells contain no
joint records. These are synthetic boundary defects, not observed corrupt
committed artifacts, wrong gate decisions or permission to interpret the
unmatched candidate comparison.

ADR-220 reuses established original probability, finite score and positive
integer history guards on these three canonical fields. Nullable probabilities,
legacy absence, strict probability >0.95, exact holdout projection checks and
GateResult behavior are preserved. No threshold, fingerprint, source, sample,
estimator, workflow or generated artifact change.

## Correction and verification

The final baseline had 23 failing rejection cases and 21 preserved cases before
code; all 139 focused joint/probability/power-array cases pass after the three
validators. Independent final review approved the complete slice and ran 213
related tests. All eight committed null artifacts (400 joint records) and all
12 committed power cells round-trip unchanged. Nullable/current power attachment,
strict threshold endpoints, exact original bounds, projection mismatch and
unchecked null/power reconstruction are covered. Full foreground delivery
verification is recorded in the session state. No generated record changes.
