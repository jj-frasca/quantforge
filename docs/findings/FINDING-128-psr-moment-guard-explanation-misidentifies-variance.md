# FINDING-128: PSR moment-guard explanation misidentifies variance

- **Date:** 2026-10-07
- **Severity:** Low — methodological explanation conflates a shape restriction and variance
- **Status:** Resolved — ADR-193; runtime guard preserved

## Evidence

Before clarification, the PSR docstring called kurtosis-skew**2-1 the variance of the Sharpe estimator and said its
nonpositive values cannot describe a distribution. The implemented standard-error factor is
instead 1-skew*observed_sr + .25*(kurtosis-1)*observed_sr**2, divided by n_returns-1.
A symmetric two-point distribution has skew zero and raw kurtosis one. At observed Sharpe zero,
benchmark zero and n_returns=100, the current guard rejects it as degenerate; the native formula
standard error is independently sqrt(1/99), approximately .10050378152592121, strictly positive.
The existing restriction excludes a boundary case; its expression is not the actual SE factor.

## Clarification and limits

ADR-193 distinguishes the retained strict Pearson moment-slack policy from the standard-error
factor in function/test notes and cold memory. Runtime guard, formula, assertions and legacy error
text remain unchanged; independent review approved the documentation-only clarification. Review its statistical/domain rationale independently before considering any
behavioral change. This finding does not authorize weakening the guard or changing thresholds;
ADR-192 preserves it exactly. No observed production false graduation or generated-data correction
is claimed. Source validity and finite arithmetic remain separate concerns.
