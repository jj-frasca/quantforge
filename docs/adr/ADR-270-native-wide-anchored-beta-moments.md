# ADR-270: Compute matched anchored beta moments for native wider returns

- **Status:** Accepted
- **Date:** 2026-10-12
- **Deciders:** Codex autonomous session 4, ISO 2026-W42
- **Resolves:** FINDING-219
- **Extends:** ADR-180, ADR-268, ADR-269

## Context

Installed pandas Series.cov converts observations to float64, while nanvar reduces
means and squared deviations in float64 even for original wider floating input.
Native wider same-series neighbors therefore publish beta zero at origin 1/.5 and
about .880141 at .1 instead of the exact covariance-ratio answer one. Correcting
covariance alone leaves an independently biased denominator and remains wrong.

## Options considered

1. Compute matched native wider moments only for actual native wider inputs.
   Preserves ordinary/nullable paths while closing demonstrated source narrowing.
2. Replace covariance alone. Rejected by independent oracle evidence: beta .4 or
   about 3.5e-7 remains wrong where the exact answer is one.
3. Rewrite every covariance/variance estimator. Wider compatibility surface than
   the reproduced defect requires.
4. Use a full native covariance matrix. Computes unused strategy self-variance
   that can underflow and unnecessarily decline an otherwise measurable beta.

## Decision

After original alignment/validation and ADR-269's exact constant check, dispatch
only when either aligned original Series has native floating np.dtype wider than
float64. Promote original retained values to np.longdouble arrays, subtract each
array's own first observation, then center each translated array with its native
mean. Compute the native centered cross-product sum and benchmark squared-deviation
sum. Sample covariance/variance share the same n-1 divisor, which cancels exactly
in beta. Divide the native sums before converting only final beta to float.

Translation preserves the covariance-ratio definition while removing the large
origin before centering. Matching numerator and denominator prevents incompatible
precision paths; no unused strategy variance is computed. Source data is untouched.
Require a positive finite native denominator. Underflow in needed wider arithmetic
becomes ValueError before the ordinary float64-based fallback can invent beta zero.
Mathematically finite beta may remain unmeasurable under this explicit limitation.

Keep the entire original nonwide ADR-268 path, exact constant beta-zero convention,
source guards, inner overlap and downstream alpha/IR/tracking-error/drawdown formulas.
Alpha naturally changes with corrected beta. The earlier wider same-series baseline
test now asserts its exact mathematical beta one. No epsilon, threshold, calibration
identity, generated-record, workflow or persistence-shape change.

## Evidence and limits

Independent scratch review: 224 exact represented-input Fraction covariance-ratio
probes pass; 160 complete ordinary/nullable outputs remain exact. Needed cross-products
preserve tiny strategy beta rounding to zero without an unused-diagonal failure;
a native denominator outside float64 range still produces beta one. Unmeasurable
needed wider moments refuse rather than masquerade as a constant benchmark.

Observe RED before production. Verify same-series/affine/mixed wider source oracles,
Hypothesis native ULP offsets, exact constant controls, partial overlap, native
source/caller-state preservation, ordinary complete baselines and capability-aware
platform behavior. Run independent review, foreground make check-all and exact CI.

Anchoring is not universal covariance precision: uneven translations, native means,
sums and extreme near-zero moments can still lose evidence or be declined. Existing
source validation arrays narrow to float64, and other comparator statistics and
ordinary scaled recovery retain their separate limits. Native wider plus nullable
floating excess subtraction is unsupported by installed pandas (KeyError before
beta); this separate compatibility defect is not corrected here. No complete strict-error-
state guarantee or claim that every finite mathematical beta becomes measurable.

## Reversal

Remove the genuine wider dispatch and helper, restoring pandas moments on that
path. This reopens FINDING-219 without changing ordinary code or gate thresholds.
