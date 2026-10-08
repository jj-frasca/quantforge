# FINDING-149: Native Sortino zero mean can lose a cancellation residual

- **Date:** 2026-10-07
- **Severity:** Medium — a representable descriptive score is published as zero
- **Status:** Resolved by ADR-207

## Evidence

Target zero with returns `[-1e100, 1e-200, 1e100]` produces native Sortino zero.
An 800-digit Decimal oracle constructed from the exact floats gives approximately
`9.16515138991168e-300`, representable in float64. Native reduction loses the
middle observation; all native output checks pass. The original excess sum via
math.fsum remains `1e-200`, so true cancellation can be distinguished from the
lost residual before the same scaled recovery used for arithmetic failure.

This is an independent offline reproduction. Sortino remains descriptive, so no
production graduate or selector effect is asserted. ADR-207 will specify tests
first and require stable original-excess evidence before accepting a native zero
mean. Normalization can itself lose information at extreme scale ratios; ratios
truly below the smallest subnormal can legitimately round to zero. No blanket
finite-precision guarantee, threshold change or generated-record rewrite follows.

## Resolution and limits

ADR-207 routes detected native moment/mean/ratio underflow to the existing scaled
recovery and requires zero original-excess fsum before preserving a native zero
mean. Twenty-nine RED regressions precede correction; exact-float 800-digit
oracles verify signed residuals and partial moments. True cancellation and tiny
ratios legitimately rounding to zero remain measured zero. Nonzero native finite
results remain unchanged; arbitrary subtraction/normalization precision and
nonzero mean cancellation are not certified. No validation identity or threshold
changes and no generated evidence is restated.
