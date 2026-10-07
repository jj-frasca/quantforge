# FINDING-136: OOS diagnostics turn missing returns into flat evidence

- **Date:** 2026-10-07
- **Severity:** Medium — undefined selection can publish finite OOS claims
- **Status:** Resolved — ADR-199

## Evidence

For the four-row matrix in FINDING-135, replacing the first row of both
candidates with NaN still publishes OOS Sharpe approximately 78.57480512 from
both evaluators. Their guarded sample-Sharpe helper treats NaN standard deviation
as the flat-return branch and gives both candidates an IS score of zero. The
positional argmax then chooses config zero on missing train evidence; finite
result fields cannot distinguish it from a measured selection. Missing/undefined
test or benchmark blocks can similarly look like measured zero Sharpe. Masked
arrays with missing observations and finite underlying values also publish
ordinary scores because array materialization discards the explicit mask.

Normal search performance is protected by PBO's complete-finite preflight, and
canonical acquisition has separate quality checks. This finding identifies direct
evaluator boundaries, not a measured production leak or false graduate.

## Correction and limits

Require every matrix and supplied benchmark value to be finite in the float64
kernel before any split selection, short/constant shortcuts or fold dropping.
Reject missing/infinite, explicitly masked or conversion-overflow evidence with ValueError. Keep
finite constant and singleton blocks, signed numeric returns, absent benchmark
semantics, score arithmetic and all thresholds. Native finite moment overflow
inside the private Sharpe kernels remains a separate numerical question.
