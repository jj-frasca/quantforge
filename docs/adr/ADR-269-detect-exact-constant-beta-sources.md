# ADR-269: Detect exact constant beta sources before moment centering

- **Status:** Accepted
- **Date:** 2026-10-12
- **Deciders:** Codex autonomous session 4, ISO 2026-W42
- **Resolves:** FINDING-218, constant-centering limitation disclosed in FINDING-217
- **Extends:** ADR-181, ADR-268

## Context

Repeated represented .1 returns have exact centered residuals zero, but pandas
rounded mean centering leaves a positive native residual variance/covariance.
A constant benchmark publishes beta 1/24; a constant strategy against a varying
benchmark publishes about 1.2e-31. No underflow is signaled, so ADR-268 properly
preserves those native results. Both values contradict the covariance definition.

## Options considered

1. Detect exact constant original aligned sources before beta moments. Narrow,
   preserves every nonconstant calculation and avoids manufacturing residuals.
2. Replace all centering/moments with a stable estimator. Wider numerical decision
   and compatibility surface than the repeated-source counterexamples require.
3. Compare float64 validation arrays or add a variance epsilon. Can erase distinct
   native wider observations or reinterpret nearly constant evidence as constant.

## Decision

After existing source/alignment/finite/positive-wealth validation, test constancy
on each original aligned Series using equality with its own first observation.
If either source is exactly constant, beta is zero: benchmark-zero dispersion
uses the existing convention, and a constant strategy has exactly zero covariance.
Bypass native and scaled beta moments in those cases. Retain the unchanged ADR-268
native/underflow/scaled path for every nonconstant pair.

Do not use float64 validation arrays for constancy. Wider original values can be
distinct even when conversion would make them all equal. Compare only aligned
observations, preserving partial-overlap semantics and original source dtypes.

All other formulas remain, including alpha with corrected beta. No epsilon, source
repair, gate threshold, calibration identity, workflow or generated-record change.
The prior .1 compatibility test changes to assert mathematically correct beta zero;
its original wrong native result remains documented historical evidence.

## Evidence and limits

Independent scratch review confirms both-sided counterexamples, 15 dtype/side
constant cases, no beta moment calls on constants and 150 complete exact ordinary
nonconstant baseline outputs. Observe RED before production edits; verify signed/
nullable/native-wide sources, source preservation, overlap, moment bypass,
Hypothesis repeated constants, original downstream alpha and exact nonconstant
compatibility. Run independent review, foreground make check-all and exact master CI.

Nonconstant nearly constant moments and native-wide centering remain separate
precision limitations. A nonconstant native-wide same-series fixture currently
publishes beta about .880141 rather than one; this slice must preserve it rather
than misclassify its original distinct values as constant. Other comparator
statistics and extreme scaled-recovery limitations are unchanged. There is no
universal numerical-precision or strict-error-state guarantee.

## Reversal

Remove the exact-source constant guard and restore the old .1 compatibility
assertion. That reopens FINDING-218 without changing source domains or thresholds.
