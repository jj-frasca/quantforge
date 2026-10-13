# ADR-276: Compute integer alpha from the unrounded OLS intercept

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** Codex autonomous session 6, ISO 2026-W42
- **Resolves:** FINDING-225
- **Extends:** ADR-269, ADR-275

## Context

ADR-275 corrects integer beta while explicitly retaining original mean/alpha
precision. At base2**60, strategy[base+2,base+3,base+4] versus benchmark
k*[base,base+1,base+2], k1 or3, has exact beta1/k and annual intercept504.
All four plain/masked 64-bit families publish alpha0 from rounded original means.
Using the rounded published beta can independently amplify rounding at large
origins; alpha must be computed as its own regression coefficient before rounding.

## Options considered

1. Exact integer OLS intercept using the same sufficient covariance sums, final
   float only. Preserves every noninteger path and the constant-source convention.
2. Substitute exact means but keep rounded beta. Can amplify beta rounding and
   misstate an otherwise small exact intercept.
3. Replace every source mean/alpha estimator. Unnecessary compatibility scope.
4. Cache moment state on the comparator. Unneeded mutable state for modest O(n)
   integer scans; simplicity and source ownership matter more here.

## Decision

For the existing supported both-original-integer domain, share ADR-275's unchanged
sufficient-sum arithmetic through a private tuple (num,den,sumS,sumB). The existing
beta wrapper keeps the same positive denominator check and final integer quotient;
its exact results and constant guard/bypass are unchanged.

When either source is exactly constant, alpha uses the existing beta-zero
convention as the exact integer mean 252*sumS/n, without covariance work.
Otherwise compute alpha as the final integer quotient
252*(sumS*den-num*sumB)/(n*den), where num/den is the UNROUNDED exact beta ratio.
Do not convert source totals, means or beta before this final alpha division.

This is the same mathematical annualized OLS intercept; it intentionally need not
match rounded published beta multiplied by rounded means. Every integer-family
alpha now follows this path, so even small adequate native results may change
rounding. Noninteger alpha/formulas, beta outputs, excess/IR/TE/drawdown, metadata,
source guards and caller state stay. No threshold, calibration identity, workflow,
schema or generated record changes.

The public nonconstant integer path may execute two streaming scans through the
shared helper, O(2n) time/O(1) additional memory. Avoid caching or complicating the
beta contract. Constants scan only the exact strategy total for alpha and do not
compute covariance. This remains small compared with normal research execution.

## Evidence and limits

Independent scratch: 600 centered Fraction annual-intercept oracles n2–128,
full uint64, large origins and both constant sides; eight public alpha0-vs504
failures. Public large fixtures preserve existing exact excess representability
on 53-bit platforms; a separate direct full-width alpha oracle retains all source
precision. Require genuine RED before code, Fraction/Hypothesis tests, original
constant/guard precedence, alignment/ownership/state and complete outside-path
plus integer-other-statistic preservation. Run independent final review, full
foreground make check-all and exact master CI before delivery.

Exact sums/intercept concern integer sources only; other source statistics,
noninteger rounding, final float representation and whole-comparator strict-state
limitations remain. No historical market contamination is established.

## Reversal

Restore the original alpha expression for integer pairs and inline the existing
beta sums again. This reopens FINDING-225 while preserving ADR-275's beta repair.
