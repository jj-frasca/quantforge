# FINDING-127: PSR accepts malformed scalar evidence

- **Date:** 2026-10-07
- **Severity:** Medium — unmeasurable statistical inputs produce ordinary probabilities
- **Status:** Resolved — ADR-192

## Evidence

With observed Sharpe .2, benchmark zero, n_returns=100, skew zero and raw kurtosis three,
probabilistic_sharpe_ratio returns 0.5 when kurtosis is replaced with infinity, approximately
.5958174220427449 when the return count is 2.5, approximately .9999999999999998 when observed
Sharpe is boolean True, and zero when benchmark Sharpe is infinity. These are valid-looking
probabilities despite nonfinite moments/benchmarks, fractional history or boolean score evidence.
The probability DSR wrapper delegates to PSR and inherits its scalar evidence boundary.

## Correction and limits

ADR-192 validates observed-return count first as a nonboolean Integral >=2, then requires finite
float-representable nonboolean Real observed/benchmark Sharpe, skew and raw kurtosis. RED tests
cover count, each source scalar and probability-wrapper propagation before correction. Preserve n_returns>=2, raw-kurtosis convention,
variance restriction, ordinary PSR/DSR formulas and gates. Consumer review found measured numeric inputs; independent signed/normal oracles and
numpy/Fraction compatibility preserve valid results. Extreme finite arithmetic and margin-form observed score validity
remain separate questions. No invalid production moment record is claimed; no generated-data edits.
