# ADR-235: Validate original band-filter process scalars

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 31, ISO 2026-W41
- **Resolves:** FINDING-185
- **Extends:** ADR-061, ADR-223, ADR-232, ADR-234

## Context

The band-state filter accepts NaN volatility/drift and infinite level volatility.
NaN process inputs can become missing forecasts and finite zero reference scores;
infinite level volatility can produce zero states and a finite score. Boolean
parameters also act as numeric source-law evidence. Source-array validation cannot
establish the validity of the model parameters used with those observations.

## Options Considered

1. Apply the shared original finite-real-nonboolean scalar guard without changing
   operands. Narrow and consistent, but rejects malformed direct callers.
2. Check only filter outputs. Cheap, but infinite level volatility can produce
   finite states and NaN outputs can be flattened downstream.
3. Convert, cap or replace parameters. Convenient, but changes valid native math
   or invents model evidence; rejected.

## Decision

Validate rho, level_vol, deviation_vol and drift with _finite_leaf_score, requiring
original finite float-representable real nonboolean evidence. Retain the original
operands in every existing range comparison, covariance and state operation.
Validate rho before its existing stationarity test; validate both volatilities
before their existing combined range test; validate drift before ADR-234 sources.
Scalar validity takes precedence for combined malformed scalar inputs. Valid
parameter range errors still precede source errors. Preserve original exact
negative comparisons, including negative real values that round to signed zero.

Keep rho in (-1,1), level_vol >=0 and deviation_vol >0; finite signed drift and
zero level volatility remain supported. Do not normalize numeric types, change
initialization, Kalman formulas, source/startup conventions, references, defaults,
thresholds, fingerprints or data. Derived arithmetic and general mixed-type
measurability remain separate. FINDING-159 is not resolved by these scalar guards.

## Verification

Observe invalid original scalar failures on empty, singleton and normal sources
before code. Protect numeric scalar operands, existing exact range checks,
stationary signed rho, signed drift and zero level volatility. Include Hypothesis
original boolean refusal and independent producer/native score comparisons.
Independent final review and full foreground make check-all precede explicit-path
commit, fresh sync, individual push and exact master CI verification.

## Consequences and reversal

Invalid process evidence cannot obtain a real reference claim through missing
estimates or a short-source shortcut. Remove the four validation calls to reverse
this decision and reopen FINDING-185; no historical calibration is restated.
