# ADR-180: Reject nonfinite benchmark statistics

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 11, ISO 2026-W41
- **Resolves:** FINDING-112
- **Extends:** ADR-112, ADR-171, ADR-179

## Context

Finite real returns do not guarantee finite intermediate moments or output statistics. Extreme
finite equal strategy/benchmark returns can publish NaN alpha and beta after covariance overflow.
Optional HTTP comparisons catch ValueError but not arithmetic exceptions from strict NumPy settings.

## Options Considered

1. Validate all published scalar statistics, declining nonrepresentable calculations. Narrow and
   reversible; retains the existing estimators and ordinary results.
2. Replace moment estimation with scaled arithmetic. Potentially accepts more extreme inputs but
   requires a separate numerical-method decision and independent estimator oracles.
3. Cap inputs or replace invalid scalars with zero. This invents evidence and hides failure.

## Decision

Preserve existing arithmetic and zero-variance conventions. Locally suppress overflow, invalid
and divide warnings during statistic computation, then require finite alpha, beta, information
ratio, tracking error and relative drawdown before publishing BenchmarkComparison. Raise
ValueError for nonfinite statistics, retaining the optional API's fail-soft behavior.
Underflow handling is unchanged; finite-but-inaccurate tiny-variance results remain the separate
FINDING-113 and are not claimed repaired. No returns are capped, repaired or removed.

## Consequences and limits

A comparator cannot publish NaN/infinite scalar claims solely because intermediate variance,
covariance, mean or annualization overflows. Some mathematically representable results are declined
when the current estimator's intermediate arithmetic cannot represent them. This is an explicit
limitation rather than a new estimator. Finite outputs alone do not certify arithmetic accuracy.
No generated data, calibration identity, validation threshold or workflow changes.

## Reversal

Remove the finite-output guard and local error handling. This reopens FINDING-112.
