# FINDING-192: Power capture arithmetic publishes invalid derived claims

- **Status:** Corrected
- **Date:** 2026-10-11
- **Severity:** Medium — derived calibration evidence
- **Scope:** PowerCalibration capture accessors and computed JSON
- **Decision:** ADR-243

## Evidence

Valid two-symbol cells with finalist/category scores [1e308, 1e308] and reference
scores [1, 1] publish infinity from all four capture accessors. With reference
scores [1e308, 1e308] and finalists [1, 1], gross capture falsely becomes zero;
net/achievable capture returns None and category capture becomes empty because
infinity <= infinity satisfies the noise refusal. Finite references [1e200,
1e200] raise native OverflowError in Lo's standard-error squaring. Unbounded
positive integer histories can also overflow native median/history arithmetic.

A singleton cell with reference 0.5, finalist/category 1e308 and 7,400 bars
isolates genuine quotient overflow while the reference exceeds the unchanged
finite noise bar. These parent and independent synthetic probes establish
invalid derived arithmetic, not corrupt committed outcomes. All 12 committed
cells currently have finite capture outputs or legitimate refusal. No sources,
searches, outcomes or generated records were changed or rerun.

## Correction and verification

ADR-243 checks finite evidence at each existing executed arithmetic stage,
preserving finite native answers and legitimate early refusals. The final
preimplementation run observed 31 failures and 18 preserved cases. Independent
review found an implicit integer-to-float inspection defect in the first patch;
three additional regressions failed before its correction. Native integer
medians now remain unchanged and their derived years are checked separately.
The 215 affected tests pass; independent review passed 52 new cases and 280
exact native computed-JSON preservation probes. All 12 committed cells retain
identical full computed JSON, and the public frontier is unchanged. Full
foreground delivery verification is recorded in the session ledger.
This does not recover unmeasurable native arithmetic, certify finite precision
or resolve reference qualifications FINDING-155/159.
