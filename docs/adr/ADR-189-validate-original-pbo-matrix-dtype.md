# ADR-189: Validate original PBO matrix dtype

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 11, ISO 2026-W41
- **Resolves:** FINDING-124
- **Extends:** ADR-104, ADR-105, ADR-106

## Context

PBO coerces its matrix to float64 before checking the source domain. Boolean, numeric string and
object matrices produce range-valid scores; complex evidence loses its imaginary components and
still produces a live gate value. ADR-106 validates converted evidence, leaving the original-source
boundary open. Direct engine/search consumers build real numeric matrices.

## Options Considered

1. Validate original array dtype before float conversion, preserving matrix-shape precedence.
2. Treat conversion warnings as validation. A warning still permits a gate-changing score.
3. Parse/repair source values. Changes supplied evidence rather than rejecting malformed inputs.

## Decision

Form the original array with np.asarray without dtype coercion. Preserve the existing two-dimensional
check first, then require dtype kind i, u or f (signed/unsigned integer or real floating point).
Reject bool, string, object, complex and temporal dtypes with ValueError. np.number alone is too
broad because it also admits timedelta64. Convert accepted evidence to float64 as before and retain
all existing configuration/split/finite/half-sample checks and CSCV/tie arithmetic unchanged.

## Consequences and limits

Malformed original evidence cannot be silently reinterpreted. Numeric arrays and nested lists,
finite constant candidates, integer/unsigned/float representations and valid matrix scores retain
their existing contract. RED dtype regressions precede the correction; existing reference CSCV,
noise, dominant-candidate and permutation/tie tests verify the estimator. No row or candidate is
dropped or imputed. pbo_max remains strictly 0.5; no valid production statistic changes, so following
ADR-106 calibration identity does not advance. No workflow dispatch or generated-data edits.
Extreme finite Sharpe arithmetic and split-count type contracts remain separate limitations.

## Reversal

Restore immediate float64 coercion. This reopens FINDING-124.
