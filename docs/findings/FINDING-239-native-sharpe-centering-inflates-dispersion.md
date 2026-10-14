# FINDING-239: Native Float64 Sharpe centering inflates represented variance

- **Status:** Corrected by ADR-290
- **Date:** 2026-10-14
- **Scope:** Primary Sharpe, native/classic Float64, positive measurable native STD

## Reproduction

Public sharpe_ratio on 1e-100+arange(3)*ulp(1e-100) accepts
7.911860051945091e16 versus exact Fraction centered sample variance and Decimal
200/800 target 1.2509749146322299e17, 36.7544% low. Native STD is positive;
variance around 1e-232 is representable and no underflow occurs. ADR-286 therefore
leaves this case outside its failed-STD recovery by design.

Other reproduced cases: .01+arange(4)*ulp(.01) gives 6.470755896124104e16 versus
7.088357936833456e16 (8.7129% low), and 1+arange(7)*ulp(1) gives
2.9600677270592188e16 versus 3.309456327853854e16 (10.5573% low).
Both signs and native/classic Float64 reproduce. Subtracting a rounded original
mean changes represented variance; finite arithmetic alone is insufficient.

## Correction and limits

ADR-290 corrects only the native-accepted original Float64 branch whose same-sign
nonzero observations lie within the inclusive factor-two magnitude range. That
range certifies exact represented anchor subtraction; normalized differences keep
centered variance measurable without near-equal source-level centering. Preserve
the actual accepted native mean and restore one exponent difference after the
annualized ratio. Ordinary same-sign rounding inside the range intentionally
changes; other dtype, mixed-sign, zero-containing, wider-spread and failed native
paths retain the prior result. This does not certify arbitrary native numerator
accuracy or universally correctly rounded moments. The existing iid interval follows the corrected primary Sharpe with its
formula/assumptions unchanged. Descriptive volatility remains separate; its native finite centering limitation is not corrected by this unit.

Primary Sharpe feeds search, holdout and graduation, so accounting advances to v13.
Current-version calibration is unmeasured; historical v12/v11/frozen v10 evidence
keeps its executed meaning. No cohort redraw, threshold change or generated-data
rewrite. No actual false graduate or historical market contamination is established.

## Evidence

Parent reproduced twelve native cases and passed 80 exact variance/known-mean
oracles. Independent scope approved 280 Fraction/Decimal controls and 207 exact
outside/failure baselines, exact translation identities, boundary/range proof and
100k-observation public prototype approximately .0036s. Public TDD and production
verification completed separately. Actual repository baseline observed 62 failures
and 49 preserved controls before production: 105 new cases, five current-version
pins and one retained nearconstant fixture strengthened to its independent
variance oracle. All original financial property domains/assertions remain.
Only then was the correction implemented; all 584 focused new/recovery/PBO/
descriptive tests passed.

Independent final thirteen-path review approved 105 new tests, exact v13 identity
and historical v12 restoration, 357 exact prior-result/source/failure/state
controls, 280 Fraction/agreeing Decimal200/800 known-native-mean variance checks,
and 48 public other-field/derived-interval controls. AST restoration certified all
old helpers, native guard/fallback arithmetic and interval formula unchanged;
PBO production was byte-identical to the preceding revision. Caller observations
and NumPy state remained. Actual 100k cost was .00159s before and .00221s after.

The first full gate stopped on three C408 keyword-dictionary fixture style errors.
Those were rewritten to identical string-key literals, retaining every number
and assertion; production arithmetic was unchanged. Actual full lint/format/mypy
and 105 new tests then passed before the required fresh full gate.

Fresh full foreground `make check-all` passed 11,158 backend tests (97.40%
coverage) and 363 frontend tests (97.63% statements), with Ruff lint/format,
strict mypy, ESLint and TypeScript green. All verification was closed at commit.
