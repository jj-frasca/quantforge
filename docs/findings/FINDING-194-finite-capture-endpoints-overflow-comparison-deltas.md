# FINDING-194: Finite capture endpoints overflow paired comparison deltas

- **Status:** Corrected
- **Date:** 2026-10-11
- **Severity:** Medium — invalid paired research evidence
- **Scope:** compare_power_sweeps capture deltas
- **Decision:** ADR-245

## Evidence

Two valid singleton power cells with gross/net reference 1, 7400 bars and finalist
scores -1e308 and 1e308 have finite capture ratios under ADR-243. Different search
versions allow compare_power_sweeps to produce net_capture_delta and capture_delta
of infinity. Default model_dump_json renders both as null, indistinguishable from
unmeasured deltas. Moving finalist names still permits attributable=True.
Independent scratch reproduction confirmed this behavior; these are synthetic
records, without an actual corrupt artifact, revised null rate or false graduate.
No actual cohort, committed power input, search or generated data was rerun.

## Correction and verification

ADR-245 requires a finite executed native difference after the existing None
refusal. The helper now checks that original subtraction result and raises
ValueError for a nonfinite delta; no failure is converted into missing evidence.

Before implementation, six overflow regressions failed and 11 preservation cases
passed. All 17 public comparison cases pass after the guard, covering both signs,
independent gross/net paths, exact finite subtraction, signed zero, subnormal
underflow, missing and unmatched cells, net-noise refusal and Hypothesis cases.
Independent review approved 321 exact full-row published-baseline JSON comparisons
over finite, extreme, missing and unmatched variants. Restoring only _delta
restores the published full-module AST; detection and attribution remain intact.

The full foreground backend/frontend delivery gate is required before shipping.
Direct comparison-row construction and wider reference qualifications remain
separate; no eligibility, attribution, estimator or threshold changes.
