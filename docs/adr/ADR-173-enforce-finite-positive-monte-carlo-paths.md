# ADR-173: Enforce finite positive Monte Carlo paths

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Codex autonomous session 28
- **Resolves:** FINDING-104, FINDING-105
- **Extends:** ADR-123
- **Supersedes in part:** ADR-123's identification of the smallest positive float

## Context

The GBM boundary accepts nonfinite parameters and invalid time increments, returning NaN/infinite
paths. Positive finite parameters can also overflow intermediate or final arithmetic. The approved
positive-floor policy uses `finfo.tiny`, the smallest normal float, although ADR-123 describes the
smallest positive float. This overwrites valid subnormal initial prices and zero-volatility paths.

## Options Considered

1. Validate finite parameters and positive time increments, reject nonrepresentable upper outputs,
   and implement the approved smallest-positive floor accurately. This preserves ordinary GBM math.
2. Cap drift/volatility. Arbitrary ceilings change the model and contradict ADR-123's reasoning.
3. Clip upper outputs or repair NaN. This invents risk observations rather than declining measurement.

## Decision

Require finite s0/mu/sigma/dt, s0>0, sigma>=0, and dt>0. Retain positive path/step count checks,
seeded RNG and the existing GBM/cumulative-product formula. Reject arithmetic overflow or any
nonfinite computed path with ValueError. Preserve positive underflow flooring, using float64's
actual smallest positive subnormal (`nextafter(0,1)`), not the smallest normal (`finfo.tiny`).
This retains valid subnormal observations and the exact initial column; genuine zero underflow
still receives the smallest representable positive floor. No arbitrary volatility ceiling.

## Consequences and limits

Undefined simulations cannot feed NaN/infinite paths into risk probabilities. Normal inputs retain
their deterministic seeded paths. The existing extreme-volatility positivity regression remains
valid; risk analysis uses unit initial wealth and losses at either tiny floor round to -100%.
Raw subnormal values change prospectively to their correct scale. No stored results, validation
thresholds, loss-threshold comparisons, estimator formulas, resource limits, or APIs are changed.
This guards path generation, not the separate risk estimator's sampling or moment methodology.

## Reversal

Restore permissive finite boundaries and the normal floor. This reopens both findings.
