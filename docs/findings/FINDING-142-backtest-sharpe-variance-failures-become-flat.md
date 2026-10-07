# FINDING-142: Backtest Sharpe variance failures become flat

- **Date:** 2026-10-07
- **Severity:** Medium — finite source observations can yield fabricated observed Sharpe
- **Status:** Resolved — ADR-203

## Evidence

The shared `sharpe_ratio` helper returns approximately 37.22902094 for a pandas
Series repeating `[.01, .02, .03]` four times. Multiplying every observation by
`1e200` or `1e-200` keeps every value finite but returns zero. Native sample
variance overflows or underflows, and the helper's native nonfinite/zero-standard-
deviation convention treats the failure as flat returns. Strict NumPy state can
instead raise FloatingPointError. These are not scale-invariant sample scores.

The helper feeds observed, holdout, lifecycle and regime statistics and the
iid-normal Sharpe interval. Source-domain validation in ADR-185 does not establish
derived-moment measurability. This direct synthetic reproduction is not evidence
that production returns reached these scales or a false graduate occurred.

## Correction and limits

Preserve the original native score whenever its mean, positive dispersion and
annualized quotient are measurable. Otherwise compute the same sample Sharpe on
returns divided by their maximum absolute value: the common positive scale cancels.
Require finite positive normalized dispersion and finite score or ValueError,
under ordinary or strict state. Engine cost/sign properties include nonconstant
tiny valid returns; rejecting all native variance underflow would break their
contract. Do not filter those property domains or impose a greater-than-minus-one
restriction on a statistical primitive. High-precision oracles verify recovery.
Valid empty/singleton and actual constant scores remain zero. Native finite
precision and finite quotient underflow remain separate numerical questions.
