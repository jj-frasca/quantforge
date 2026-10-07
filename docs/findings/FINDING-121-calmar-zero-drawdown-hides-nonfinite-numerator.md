# FINDING-121: Calmar zero drawdown hides a nonfinite numerator

- **Date:** 2026-10-07
- **Severity:** Low — public descriptive helper lacks scalar input validation
- **Status:** Open — separate scalar-domain review required

## Evidence

calmar_ratio(annualized_return=inf,max_drawdown=0.0) returns 0.0. The zero-drawdown shortcut
bypasses numerator validity; the same call with NaN also returns zero. ADR-108's convention
represents finite performance with no drawdown, not a nonfinite source annual return.

## Next action and limits

Review the finite scalar and drawdown domain, validate before shortcuts and preserve finite ratio
semantics. No claim of a production caller failure: standard composed metrics validate compounded
wealth first. Arithmetic overflow and possible domain choices need independent evidence before a
correction. No validation thresholds or generated records should change.
