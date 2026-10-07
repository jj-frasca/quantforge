# ADR-201: Refuse unmeasurable native PBO moments

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 13, ISO 2026-W41
- **Resolves:** FINDING-138, FINDING-139
- **Extends:** ADR-106, ADR-105, ADR-200

## Context

Complete finite observations do not imply measurable float64 sample moments.
FINDING-138 shows native variance overflow and underflow fabricating zero Sharpe
ties and moving PBO from 0.0 to 1.0 under a common positive scale change.
FINDING-139 also shows native rounding inventing positive dispersion for exact
constant columns, producing PBO 0.0 instead of their defined flat result 1.0.

## Decision

At the cached sample-Sharpe helper, identify exactly constant columns from their
observations; their existing defined score remains zero without using moment arithmetic.
Compute moments on the original block layout, validating and dividing only nonconstant
columns, with local overflow,
underflow and invalid handling. For nonconstant columns require finite means,
finite strictly positive standard deviations, and finite quotient scores.
Unmeasurable arithmetic raises ValueError before selection or ranking, under
either ordinary or strict ambient NumPy error mode.

This guard runs on every balanced subset, including OOS evidence. Do not rescale,
drop columns, invent dispersion, change ranks or relax the strict PBO threshold.
Complete representable nonconstant arithmetic remains unchanged. Correcting false
finite constant scores changes existing results, so advance the explicitly versioned
calibration accounting identity to `whole-search-budgeted-robust-iqr-pbo-ties-constant-v6`.
Old calibration remains attributable to its original identity and cannot match the
corrected procedure. New component rates are unmeasured until authorized sole-writer
calibration refresh; this decision does not authorize that refresh.
No generated data or workflows are edited or dispatched.

## Alternatives considered

- Treat overflow/underflow as flat evidence: invents a statistical tie.
- Rescale moments: a separate estimator implementation requiring wider numerical review.
- Reject all zero standard deviations: contradicts the explicit constant-candidate contract.
- Let ambient FloatingPointError escape: makes the public refusal depend on caller state.

## Verification and limits

RED tests cover large/small finite scaling under ordinary and strict error modes,
nonconstant mean overflow, and true huge/tiny/zero constants. Existing independent
CSCV, noise, dominance and tie/permutation tests protect representable arithmetic.
An independent exact-constant oracle, the finite gate-changing regression, and
new-identity/old-identity mismatch assertions protect the corrected flat convention.
An explicit cancellation regression preserves the original reduction layout;
column filtering before moments must not change finite nonconstant arithmetic.
The change certifies native moment measurability, not exactness of every finite
rounded result. Cancellation and finite quotient underflow remain separate.

## Reversal

Restore the unconditional guarded division and the v5 accounting identity. That
reopens FINDING-138 and FINDING-139 and restores their recorded historical semantics.
