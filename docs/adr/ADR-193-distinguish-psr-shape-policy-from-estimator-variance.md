# ADR-193: Distinguish PSR shape policy from estimator variance

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 11, ISO 2026-W41
- **Resolves:** FINDING-128
- **Extends:** ADR-054, ADR-192

## Context

PSR's explanatory notes call kurtosis-skew**2-1 the estimator variance and say nonpositive values
cannot describe a distribution. That expression is instead the slack in Pearson's population-moment
inequality. Equality can describe a genuine two-point distribution. The actual PSR standard-error
factor also depends on observed Sharpe; the current strict shape guard excludes some inputs whose
computed SE factor would be positive. Independent symbolic/numeric review confirmed the mismatch.

## Decision

Clarify the function notes, related test docstring and validation cold memory: the strict positive
moment slack is the existing retained domain policy; the actual SE-squared expression is
(1-skew*SR + .25*(kurtosis-1)*SR**2)/(n_returns-1). Equality distributions can exist, and the shape
policy is distinct from evaluating that expression for one Sharpe.

This is documentation only. Keep every runtime expression, guard, assertion, variable name and
legacy error text unchanged. This ADR authorizes no relaxation of the shape restriction, threshold,
calibration identity or gate. Any future behavioral proposal requires independent methodology
review under the hard limits; none is made here.

## Consequences and limits

Readers can distinguish a deliberate input policy from an estimator's actual variance factor.
The symmetric two-point example and existing formula establish the distinction without new runtime
tests that duplicate implementation. Existing mathematical tests and mandatory full gate verify
unchanged behavior. The legacy error label remains for compatibility and must be read with this
clarification. No generated records or workflows change.

## Reversal

Restore the incorrect explanatory text; runtime behavior remains identical.
