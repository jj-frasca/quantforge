# FINDING-104: Monte Carlo paths can be nonfinite

- **Date:** 2026-10-04
- **Severity:** High — undefined paths can enter simulated risk evidence
- **Status:** Resolved by ADR-173

## Evidence

`MonteCarloSimulator.simulate` checks only sign and positive counts. NaN drift/volatility/initial
price/time increments bypass sign checks; infinite drift returns infinite paths; negative dt returns
NaN via square root. Finite parameters can also overflow compounded wealth. Positive flooring does
not repair NaN or infinity. Downstream comparisons with NaN are false, so loss indicators can look
artificially safe even while return percentiles are undefined.

## Correction and limits

ADR-173 requires finite parameters, positive time increments, and finite computed paths, declining
undefined arithmetic rather than capping volatility or inventing observations. This is an offline
boundary reproduction, not evidence of a malformed committed risk report. The separate estimator's
missing-observation/moment conventions remain outside this correction.
