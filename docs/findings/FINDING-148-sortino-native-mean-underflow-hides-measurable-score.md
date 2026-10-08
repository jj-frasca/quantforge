# FINDING-148: Sortino native mean underflow hides a measurable score

- **Date:** 2026-10-07
- **Severity:** Medium — finite descriptive score can conceal lost mean evidence
- **Status:** Open

## Evidence

Target zero with returns `[-1e-160, 1e-160, nextafter(0,1)]` yields Sortino zero.
An exact-float Decimal oracle at 800 digits gives approximately
`4.5281864406895124e-163`, a representable float64 score. Native mean divides
the smallest positive subnormal by three before the ratio, losing information.
ADR-205 checks finite native mean/dispersion/score, so the finite zero is retained.

## Next decision and limits

ADR-206's target correction preserves default-target native arithmetic and does
not resolve this independent case. A future precision policy needs its own ADR,
observed failing tests and independent high-precision oracles, while retaining
full original financial property domains. Partial downside-square underflow and
normalization-rounding deserve review in the same evidence audit; no complete
solution is claimed here. Tiny ratios legitimately below float64 range must not
be confused with recoverable mean loss. Sortino remains descriptive only; no
gate/selector/calibration effect or production false graduate is asserted.

## Independent partial-moment evidence

Target `1e-161` and returns `[0,1]` also retain a finite native score with roughly
0.6% relative error against Decimal. The native negative shortfall square lies in
subnormal range, so its finite nonzero value loses precision. Target `1e-160`
yields about 5.57e-6 relative error. These are distinct from target cancellation
and remain outside ADR-206. New target precision properties use a fixed binary
excess grid; original engine financial property domains are unchanged.
