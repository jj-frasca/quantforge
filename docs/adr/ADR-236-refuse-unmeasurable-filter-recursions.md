# ADR-236: Refuse unmeasurable band-filter recursions

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 31, ISO 2026-W41
- **Resolves:** FINDING-186
- **Extends:** ADR-061, ADR-234, ADR-235

## Context

Finite original model parameters do not imply measurable native covariance
arithmetic. Squaring tiny deviation volatility can underflow covariance to zero;
squaring large volatility can overflow. Missing estimates then become flat
forecasts, and infinite observation noise can even produce finite zero estimates.
Checking only final estimates therefore cannot establish valid filter evidence.

## Options Considered

1. Refuse nonfinite derived quantities and nonpositive residual variance. Narrow,
   preserves measurable native arithmetic, but rejects extreme direct callers.
2. Check only final states. Misses infinite noise producing finite zero estimates.
3. Rescale, floor or replace covariance. Could recover some inputs, but changes
   the numerical method and requires a separate specification; rejected here.

## Decision

After existing original scalar and observation guards, validate finite initialized
process/observation noise and covariance. At each update require finite innovation,
predicted state/covariance, residual and residual variance; residual variance must
be strictly positive before division. Require finite gain and updated state and
covariance before publishing an estimate. Translate native overflow or floating
point arithmetic exceptions into ValueError. Suppress local NumPy numerical
signals and inspect the calculated values, preserving the caller's error policy.
Underflow itself is permitted: zero level noise, semidefinite matrices and harmless
decaying entries remain valid; an underflowed zero residual variance is refused.

Finite checks may convert a separate array to float64 for inspection only, to
support native object arrays such as Fraction covariance. Never replace the
calculated quantities with that view; compare original residual variance to zero.
Retain original operands, operation order, formulas and initialization. Do not
require every covariance element to be positive, substitute converted scalars,
change source/startup conventions, clip, floor or recover states. Empty and
singleton ordinary histories retain their existing empty/startup-NaN outputs;
nonfinite initialized model arithmetic is refused even without an update. This
is a finite-measurability contract, not a precision or conditioning guarantee.
FINDING-159's reference return and initialization qualifications remain Open.
No default, threshold, fingerprint or historical artifact is changed.

## Verification

Before implementation reproduce finite scalar overflow/underflow refusal failures
and preserve ordinary, signed, zero-level-noise, empty and singleton cases. Cover
native Python/NumPy overflow, strict NumPy error policies, extreme finite source
innovations and property-based unmeasurable variance refusal. Compare exact native
outputs, ownership, producers and gross/net scores independently. Full foreground
make check-all and independent review precede individual delivery and exact CI.

## Consequences and reversal

Unmeasurable recursions cannot become finite reference claims through missing or
zero states. Removing the arithmetic guards reopens FINDING-186; no historical
calibration or reference optimality claim is restated. Per-update validation adds
runtime: one independent 7400-row local filter probe took about 0.125s before and
0.363s after guarding. This is a filter-only observation, not a pipeline benchmark.
