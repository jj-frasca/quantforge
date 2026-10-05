# ADR-175: Stabilize Monte Carlo expected-return overflow

- **Status:** Accepted
- **Date:** 2026-10-05
- **Deciders:** Codex autonomous session 1, ISO 2026-W41
- **Resolves:** FINDING-107
- **Extends:** ADR-173, ADR-174

## Context

Finite GBM terminal returns can have a nonrepresentable intermediate sum, although their
arithmetic mean lies within their finite range. NumPy then publishes infinity as expected return.

## Options Considered

1. Preserve the native mean when finite, and use a scale-normalized arithmetic mean on overflow.
   This preserves ordinary results and the estimator's definition.
2. Reject the report. Safe but discards a representable statistic.
3. Clip terminal returns. Changes the modeled observations and expected return.

## Decision

Compute the existing mean with intermediate overflow locally ignored. If it is nonfinite, divide
all terminal returns by their maximum absolute value, take their mean, then restore the scale.
Finite positive GBM wealth makes terminal returns bounded below by -1; their normalized mean is
bounded in [-1, 1], so this avoids a nonrepresentable sum. Zero scale never reaches the fallback:
the native all-zero mean is finite. No sample, path, percentile, loss comparison or seed changes.

## Consequences and limits

Ordinary finite means retain their original floating-point result. Extreme means remain finite
without an arbitrary output cap. Normalization can lose negligible small terms relative to huge
returns, as ordinary finite-precision means already do. This fixes terminal-return averaging only;
moment estimation, percentile interpolation and artifact validation remain separate boundaries.
No generated evidence, API schema, resource limits or validation threshold changes.

## Reversal

Restore the direct np.mean call; this reopens FINDING-107.
