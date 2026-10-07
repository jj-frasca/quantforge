# FINDING-143: Constant backtest returns fabricate Sharpe and moments

- **Date:** 2026-10-07
- **Severity:** Medium — exact constant evidence can invent a positive score and PSR inputs
- **Status:** Resolved — ADR-203

## Evidence

For `pd.Series([0.1] * 6)`, `sharpe_ratio` returns approximately 1.0442137426e17
and `return_moments` returns `n_returns=6, skew=0.0, kurtosis=3.0`. Every supplied
return is exactly equal. The rounded native mean produces tiny false variance,
while pandas supplies its constant-series skew/excess-kurtosis convention.
Existing contracts instead define constant sample Sharpe zero and higher moments
unmeasured (`None`). A longer constant history can also inherit a false center
and scale in the descriptive iid-normal interval through the same Sharpe helper.

These synthetic primitive results can feed the live observed Sharpe and the
probability-form PSR inputs. They do not establish a production false graduate.
The existing cross-sectional healthy-factor test used exactly constant 0.004
returns and relied on this false rolling Sharpe to hold. Its fixture now uses
genuine low dispersion at the same positive mean; a separate exact-constant
regression requires retirement under unchanged floor/benchmark policy.

## Correction and identity

Recognize exact constant observations before moment arithmetic: Sharpe zero,
return moments None. Do not use a variance epsilon or collapse nearly constant
observations. Preserve complete source validation before shortcuts, signed and
nullable numeric samples, native estimators and interval assumptions. Correcting
finite score/moment evidence changes the searched procedure, so advance calibration
accounting identity beyond v7. Retain historical identities/artifacts; do not
claim refreshed rates, edit generated data, or dispatch calibration.
