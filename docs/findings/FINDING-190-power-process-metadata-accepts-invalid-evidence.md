# FINDING-190: Power process metadata accepts invalid original evidence

- **Status:** Corrected
- **Date:** 2026-10-11
- **Severity:** Medium — calibration provenance boundary
- **Scope:** PowerCalibration phi, half_life, deviation_share
- **Decision:** ADR-241

## Evidence

Each optional process field accepts True as 1.0 and the string "0.5" as 0.5.
Each retains NaN and either infinity. These are not original finite real
nonboolean process evidence. collect_power_sweep reconstructs cells but uses the
same coercive fields, so unchecked copies bypass the intended boundary as well.
The independently reproduced defect affects record provenance and ordering; it
does not establish that committed scores or process draws changed.

## Correction and verification

ADR-241 adds one before-coercion validator using the established finite leaf
guard. The final preimplementation run observed 58 failures and 32 preserved
cases; an initial refusal-message mismatch was corrected before that baseline.
Independent final review passed 353 affected tests and 94 additional boundary
probes. All 12 committed power cells retain identical normalized JSON and sweep
behavior in a read-only census. Removing the validator restores the baseline
module AST exactly. Full foreground delivery verification is recorded in the
session ledger.
Keep None/absence, normalization and finite domains; do not infer generator-law
validity or family completeness. FINDING-155 and FINDING-159 remain Open.
