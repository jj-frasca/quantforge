# ADR-196: Validate dispersion family and finite native scale

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 13, ISO 2026-W41
- **Resolves:** FINDING-131, FINDING-132
- **Extends:** ADR-046, ADR-050, ADR-190

## Context

The shared whole-search dispersion helper coerces boolean/string candidate scores
and flattens malformed nested families. Finite original scores can independently
overflow native IQR/sample dispersion and publish infinity. Downstream expected-
max checks protect finite publication but do not establish this primitive's own
source and output validity.

## Options Considered

1. Validate original scalar elements and refuse nonfinite native dispersion.
2. Check only converted array dtype. Loses mixed-list booleans and excludes
   float-representable Fraction values the existing kernel accepts.
3. Rewrite scaled variance/quantile arithmetic. Separate precision work requires
   independent numerical evidence; this decision only establishes validity.

## Decision

Preserve the at-least-two-family-elements check first. Require every original
element to be a nonboolean numbers.Real scalar, normalize to float, and require
finiteness. Nonrepresentable and nested evidence raises ValueError. Build the
one-dimensional float array only from these checked values. Keep the same native
sample standard deviation below four candidates and Normal-consistent IQR above
that boundary. Locally ignore NumPy overflow/invalid signals in this calculation,
then require finite dispersion before applying the unchanged 1e-6 floor.

## Consequences and limits

Both whole-search forms share one validated family and cannot price malformed
scores or publish an undefined native scale. Tests precede code, cover both
branches and consumer propagation, and retain signed/numpy/Fraction, flat-family,
floor and order invariance. Mathematical extreme scales may remain unmeasured;
this is refusal rather than recovery. No candidate count, estimator, floor,
threshold, calibration identity, generated record or workflow changes.

## Reversal

Restore unchecked coercion and native output publication. This reopens both
findings; downstream accounting guards would still protect normal persistence.
