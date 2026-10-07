# ADR-181: Recover beta from collapsed benchmark variance

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 11, ISO 2026-W41
- **Resolves:** FINDING-113's collapsed-variance case
- **Extends:** ADR-112, ADR-180

## Context

A nonconstant benchmark at tiny scale can have sample variance underflow to exactly zero. The
comparator then mistakes it for a constant benchmark and publishes beta zero, even against itself.
Finiteness validation cannot detect this because the incorrect beta and alpha are finite.

## Options Considered

1. Scale covariance/variance only when native variance is zero but original observations differ.
   This preserves ordinary arithmetic and the true constant-benchmark convention.
2. Replace all moment arithmetic. Wider compatibility/numerical surface than the reproduced case.
3. Add a variance epsilon or treat all tiny observations as constant. This changes the estimator.

## Decision

Compute native benchmark variance with local underflow suppression. If it is positive, preserve
the existing covariance/variance calculation. If it is zero and original aligned observations are
nonconstant, separately normalize strategy and benchmark by their maximum absolute magnitudes,
compute normalized sample covariance/variance, then restore beta's scale ratio. An all-zero strategy
has beta zero. Require positive finite normalized benchmark variance; retain ADR-180's finite-output
check. Genuinely constant benchmarks keep beta zero. Alpha and all other statistics remain unchanged.
No numerical epsilon, return clipping, gate threshold or new estimator is introduced: scaling uses
the same sample covariance ratio in a representable range.

## Consequences and limits

Identical tiny nonconstant returns recover beta one and alpha zero. Tiny affine cases agree with
an independent Decimal covariance oracle. Positive native variance and other scalar computations
retain their current behavior. Positive but subnormal variance quantization, covariance underflow
when native variance stays positive, and tracking-error/IR precision are outside this slice.
Extreme scale ratios can still be unrepresentable and are explicitly declined rather than capped.
This correction does not certify every floating-point statistic. No generated data or workflows change.

## Reversal

Remove the zero/nonconstant scaled branch and local variance underflow handling. This reopens
FINDING-113's collapsed-variance defect.
