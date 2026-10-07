# FINDING-125: Probability DSR invalid trials remove the haircut

- **Date:** 2026-10-07
- **Severity:** Medium — public multiplicity primitive accepts invalid accounting inputs
- **Status:** Resolved — ADR-190

## Evidence

On observed per-period Sharpe .2, n_returns=100, skew=0 and raw kurtosis=3, the public
probability-form DSR returns approximately .9756019368039752 for each invalid accounting pair:
(n_trials=0,sr_std=.2), (-5,.2), (100,-.2) and (100,0). The expected-max helper maps nonpositive
trial counts to its no-penalty shortcut; negative/zero dispersion leads to a nonpositive haircut
which is clamped to zero. Thus invalid accounting produces an ordinary unpenalized probability.
The margin-form deflated_sharpe already rejects trial counts below one and nonpositive dispersion,
but the probability wrapper bypasses those checks.

## Correction and limits

ADR-190 validates shared expected-max inputs before the one-trial shortcut: positive nonboolean
integral count and finite positive float-representable real dispersion. Both wrappers use the
shared guard; duplicate margin sign checks are removed. RED regressions cover all three entry
points. Ordinary formulas, N=1, gates and calibration identity remain; numpy/Fraction scalar
compatibility is protected.
No production corrupt accounting observed; Trial and whole-search boundaries normally supply
valid counts/dispersion. Numerical large-count quantiles and PSR finite-output validity are separate.
