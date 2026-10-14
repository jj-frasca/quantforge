# FINDING-237: Sortino recovery changes original cancellation evidence

- **Status:** Corrected by ADR-288
- **Date:** 2026-10-14
- **Scope:** Descriptive Sortino, original native/classic Float64, target zero

## Reproduction

Public sortino_ratio on [-3e-200,1e-200,2e-200] returns
-5.087681048627602e-16 despite exact Fraction/math.fsum total zero. Advancing the
last observation by one ULP, 2.900835519859558e-216, gives accepted score
5.087681048627602e-16 versus exact Fraction/Decimal800 8.862198898915333e-16,
about 42.59% low. Two ULPs give 1.5263043145882805e-15 versus
1.7724397797830665e-15; eight give 6.613985363215882e-15 versus
7.089759119132266e-15. Both native and nullable Float64 reproduce under strict
NumPy state, with complete finite signed samples.

Native downside squares underflow; common-scale normalization rounds observations
before stable summation. fsum cannot recover a sum erased before its input.
ADR-206/207/210 explicitly left normalization precision as a limitation.

## Correction and limits

ADR-288 specifies original fsum numerator and separately scaled original negative
RMS only for default-target original Float64 finite failed downside arithmetic.
Native measurable, nonfinite downside, mean/ratio-only failure, nonzero target,
other dtypes and uncertifiable sum-overflow retain the previous path. Genuine
zero, subnormal, legitimate signed zero and overflow None conventions remain.
Selected Fraction/Decimal oracles and exact squared subnormal midpoint controls
state a one-output-ULP bound, not universal correctly rounded recovery.

These fixtures have tiny ratios; no material market impact, false graduation or
historical contamination is established. Sortino is descriptive. Accounting v11,
current calibration unmeasured, frozen historical cohorts, thresholds and generated
records retain their meaning. No new calibration dispatch or paid resources.

## Evidence

Independent scratch scope approved 252 Fraction/Decimal200/800 oracles and 28
additional signed/subnormal controls; 100k observations took approximately .0075s.
Initial baseline observed 70 failures and 45 preserved controls, including one
invalid tiny-longdouble mock fixture: real square underflow occurred before the
injected mean operation. That fixture was corrected before production to ordinary
observations with the same injected failure and outside-family exclusion. Final
baseline observed 69 genuine failures and 46 preserved controls. Only then was
the correction implemented; all 491 focused new/existing Sortino/engine tests passed.

Independent final five-path review approved 115 new tests, 876 exact original-HEAD
ordinary/outside/nonzero-target/nonfinite/sum-overflow comparisons (including real
tiny-wide samples), 1,512 Fraction/Decimal200/800 cancellation checks, 32 exact
rational subnormal/signed-zero controls and twelve complete public other-field
comparisons. Mean/ratio-only results, caller observations and NumPy state remain
unchanged; AST comparison confirms surrounding production functions/classes and
the complete previous fallback suffix unchanged.

Full foreground `make check-all` passed 10,985 backend tests (97.43% coverage)
and 363 frontend tests (97.63% statements), with Ruff lint/format, strict mypy,
ESLint and TypeScript checks green.
