# FINDING-126: Expected-max Sharpe publishes nonfinite haircuts

- **Date:** 2026-10-07
- **Severity:** Low — extreme finite accounting produces a nonfinite derived threshold
- **Status:** Open — separate numerical/output boundary review required

## Evidence

Research expert independently reproduced expected_max_sharpe(10**17,.2) returning infinity because
both CDF arguments round to one. The corresponding Gaussian quantiles are mathematically finite.
expected_max_sharpe(100,1e308) also returns infinity, this time because the final dispersion scaling
overflows. Validating positive finite source counts/dispersion alone does not prevent either result.

## Next action and limits

Evaluate Gaussian quantiles from their upper-tail probabilities where representable, then decline
unrepresentable/nonfinite derived haircuts. Separate numerical evaluation of the same estimator
from altered multiplicity counts, arbitrary caps or changed thresholds. Use independent forward-tail
oracles before correction. These are extreme inputs; no production lifetime count at this scale is
claimed. Do not change generated records or calibration procedure.
