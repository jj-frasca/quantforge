# FINDING-186: Unmeasurable filter arithmetic can become finite reference scores

- **Status:** Corrected by ADR-236
- **Date:** 2026-10-11
- **Scope:** Direct band-filter native covariance arithmetic, after ADR-235
- **Decision:** ADR-236

## Evidence

On logarithms of closes [100,101,100,101,100], rho=0.5 and drift=0.0003, all original
observations and parameters are finite and valid. level_vol=0 and
deviation_vol=1e-200 produce all-missing estimates and reference Sharpe zero.
NumPy float64 level_vol=1e200 with deviation_vol=0.02 produces startup NaN then
zero estimates and finite reference Sharpe about -4.085063. NumPy float64
deviation_vol=1e200 with level_vol=0.01 produces all-missing estimates and
reference Sharpe zero. Scores use the established lagged forecast
(0.0003 - 0.5 * estimate).shift(1). Independent review reproduced all three
direct failures.
Python float volatility squaring can instead raise unclassified OverflowError.

For ordinary level/deviation volatility 0.01/0.02, common scales 1, 1e-150 and
1e150 produce the same finite estimates up to ordinary rounding; scale 1e-200
loses the mathematically scale-invariant gain and becomes missing. This identifies
native covariance measurability, not invalid original process evidence. No
corrupt committed artifact, changed search or changed power count is inferred.

## Correction boundary

Refuse nonfinite initialized and recursive quantities, and nonpositive residual
variance before division. Preserve native arithmetic, valid semidefinite matrices,
zero level noise and startup NaN. No scaling recovery, floors, precision guarantee,
reference reinterpretation or initialization change. FINDING-159 remains Open.

## Verification

Pre-code TDD observed 33 failures and 20 preserved cases before implementation.
Refusal cases include Python/NumPy noise overflow, underflowed residual variance,
overflowed source innovations and recursive residuals with finite innovations.
Preserved cases include signed rho, zero level noise, empty/startup outputs and
native float32/Fraction golden estimates. Parent affected suite passed 378 tests;
independent focused suite also passed 378 tests. Final review approved all five
paths with 159 independent checks: 90 exact native/ownership comparisons, three
long scaled histories, 24 producer fields, 24 gross/net references, 15 refusal and
policy/ownership checks, and three strict-policy semidefinite histories. Native
arithmetic expressions remained unchanged. Full foreground make check-all passed
4447 backend and 363 frontend tests; lint, types and coverage remained green.
