# FINDING-126: Expected-max Sharpe publishes nonfinite haircuts

- **Date:** 2026-10-07
- **Severity:** Low — extreme finite accounting produces a nonfinite derived threshold
- **Status:** Resolved — ADR-191

## Evidence

Research expert independently reproduced expected_max_sharpe(10**17,.2) returning infinity because
both CDF arguments round to one. The corresponding Gaussian quantiles are mathematically finite.
expected_max_sharpe(100,1e308) also returns infinity, this time because the final dispersion scaling
overflows. Validating positive finite source counts/dispersion alone does not prevent either result.

## Correction and limits

ADR-191 evaluates the same Gaussian quantiles from representable upper tails, using integer
true division for reciprocal counts; unrepresentable tails or final haircuts raise ValueError.
Seven failing large-count/direct-wrapper overflow cases preceded correction. Independent brentq
inversion of forward erfc verifies large-count estimates, including 10**309. Separate numerical evaluation of the same estimator
from altered multiplicity counts, arbitrary caps or changed thresholds. Ordinary-scale oracles retain the same estimator within floating-point precision. These are extreme inputs; no production lifetime count at this scale is
claimed. Do not change generated records or calibration procedure.
