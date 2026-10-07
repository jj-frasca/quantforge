# FINDING-130: PSR overflow publishes an unmeasured probability

- **Date:** 2026-10-07
- **Severity:** Medium — undefined native arithmetic can appear as measured probability
- **Status:** Resolved — ADR-195

## Evidence

With finite observed Sharpe `1e153`, benchmark zero, skew zero, raw kurtosis `1e10`
and 100 returns, PSR returns exactly 0.5. The numerator is positive; independent
high-precision arithmetic gives a standardized score approximately 0.0001989975,
whose Gaussian CDF is approximately 0.5000793885. The native SE numerator overflows
to infinity, so dividing the score by an infinite SE fabricates a zero score.
At larger finite scores, Python exponentiation instead raises OverflowError;
whole-search probability accounting catches only ValueError and therefore cannot
record this as unmeasured. A huge integral sample count can similarly overflow
conversion during division; a small representable SE-squared can underflow to zero.

No corrupt production record or false graduate is claimed. Probability DSR is a
diagnostic; the live gate retains the selection-adjusted margin. The strict Pearson
slack policy is unchanged by this finding (ADR-193).

## Correction and limits

Reject nonfinite native moment slack or SE-squared and nonpositive SE-squared before
publishing a probability. Convert native arithmetic overflow to ValueError, which
the existing whole-search consumer maps to None. Retain source checks, formula,
strict moment policy and Gaussian CDF saturation for representable SE inputs.
This declines unmeasurable native arithmetic; it does not introduce a higher-
precision estimator, arbitrary caps, threshold changes or generated-data rewrites.
