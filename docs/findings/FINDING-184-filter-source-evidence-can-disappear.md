# FINDING-184: Invalid band-filter observations can disappear into forecasts

- **Date:** 2026-10-11
- **Severity:** Medium — malformed source evidence can yield finite reference scores
- **Status:** Corrected by ADR-234
- **Affected:** filtered_deviation direct source boundary
- **Reproduced revision:** 325a8337852585d0fb5d88127ae4048b298ef201

## Reproduction

With rho=.5, level_vol=.01, deviation_vol=.02 and drift=.0003,
log prices [4.6,4.61,NaN,4.6,4.61] produce a first unmeasured state,
then .00388 and missing remaining states. Feeding the existing lagged filter
forecast (.0003-.5*estimate).shift(1) to reference scoring on coherent closes
[100,101,100,101,100] produces finite Sharpe 7.937253933193771: missing
observations have become flat forecasts instead of invalid source evidence.
Complex log prices can produce real estimates with discarded-imaginary warnings
and a finite downstream score. Numeric object arrays and malformed singleton or
empty sources are also accepted. Independent research review reproduced these
direct-call defects. No corrupt generated artifact, new search or changed
calibration rate is inferred.

## Correction boundary

ADR-234 requires original one-dimensional real nonboolean numeric complete
finite log-price observations before recursion and shortcuts. Masked missing
observations are missing evidence. Preserve signed logs, valid empty/singleton
and first-unmeasured output, original source arithmetic and all ordinary filters.
No filling, dropping, retyping, parameter/initialization changes or new optimality
claim. FINDING-159 remains Open; thresholds and generated records stay unchanged.

## Verification

TDD observed 37 failures and 16 preserved cases before the source guard.
All 56 final focused tests passed, including Hypothesis missing-source refusal
and causal-prefix invariance, retained parameter precedence and caller NumPy
error-state checks. Independent review verified 107 additional checks: 48 exact
native filter/ownership comparisons, six unchanged band producers, 24 exact
gross/net reference scores, malformed source refusal and strict error-state
restoration. Three caller-error-state preservation cases were added after the
initial TDD run; they are not claimed as additional observed failures.
Fresh full foreground make check-all passed 4,268 backend tests (97.67%
coverage) and 363 frontend tests (97.63% statements), with lint/types green.
