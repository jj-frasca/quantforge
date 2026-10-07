# FINDING-121: Calmar zero drawdown hides a nonfinite numerator

- **Date:** 2026-10-07
- **Severity:** Low — public descriptive helper lacks scalar input validation
- **Status:** Resolved — ADR-188

## Evidence

calmar_ratio(annualized_return=inf,max_drawdown=0.0) returns 0.0. The zero-drawdown shortcut
bypasses numerator validity; the same call with NaN also returns zero. ADR-108's convention
represents finite performance with no drawdown, not a nonfinite source annual return.

## Correction and limits

ADR-188 validates both original inputs as finite float-representable real nonboolean scalars
before zero-drawdown shortcuts. Finite signed scalars and absolute-denominator ratio semantics
remain; no new drawdown or return bounds. Failing shortcut/domain tests preceded the correction. No claim of a production caller failure: standard composed metrics validate compounded
wealth first. FINDING-123 independently records finite quotient overflow, resolved by the same ADR. No validation thresholds or generated records should change.
