# FINDING-179: Finite cost can overflow reference-score arithmetic

- **Date:** 2026-10-09
- **Severity:** Medium — a false finite effect-size score can be reported
- **Status:** Corrected by ADR-229
- **Affected:** oracle_sharpe_of and historical/explicit-drift AR wrappers

## Evidence

Deterministic positive closes [100, 101, 100, 101, 100], phi=-0.3 and drift=0 give
positions [0, -1, 1, -1] and turnover [0, 1, 2, 2]. Before ADR-229, finite cost
1e200 makes the shared and AR reference scorers return -0.0 as sample variance
overflows to infinity. Finite cost 1e308 produces NaN from doubled turnover cost.
Neither result is a measured finite reference effect size.

Independent dimensionless earned returns `position*return/cost - turnover` give
finite sample-ddof=1 annualized Sharpe -20.725478391232723 at both costs. This
calculation diagnoses overflow; it is not a proposed production fallback or a
claim of reference optimality. At ordinary cost 0.001 the native deterministic
score is 23.6719766198386. No random paths, searches, new observations, selected
outcomes, corrupt committed artifact or changed candidate result were observed.

## Correction boundary

ADR-229 refuses nonfinite derived returns, sample statistics and annualized
scores in the shared scorer. Preserve original finite arithmetic and genuine
zero-variance/short-history behavior. Do not repair with scaled arithmetic,
filter bad derived observations, change defaults/thresholds/identities, fit
parameters, replace reference methods, relabel historical results or write data.

## Correction and verification

The shared scorer now refuses nonfinite net-return elements before dropna,
nonfinite sample standard deviation or mean before zero-variance handling,
and a nonfinite final score. Wrappers inherit this refusal. Finite ordinary
arithmetic, short histories, missing-mean flat startup and genuine finite
zero variance retain their prior behavior; no scaled replacement is used.

TDD observed six failures and 16 preserved cases before the correction. All
90 targeted reference/AR/legacy cases passed, including exact native ordinary
gross/net arithmetic and finite huge costs on genuinely flat positions.
Independent review passed 71 cases: all 22 new cases, 46 AR cases and three
legacy/cost/known-conditional-mean consumers. Only oracle_sharpe_of changed in
production; arguments, defaults and all other functions/classes/fingerprints
remain unchanged. Full foreground `make check-all` passed 3,873 backend and
363 frontend tests, including lint, typing and coverage.
