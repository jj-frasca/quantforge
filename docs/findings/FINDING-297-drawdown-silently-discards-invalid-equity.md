# FINDING-297: Drawdown silently discards invalid equity evidence

- **Date:** 2026-10-24
- **Status:** Resolved by ADR-357
- **Area:** Raw backtesting max_drawdown primitive

## Evidence

At `c2622145`, max_drawdown computes equity/equity.cummax()-1 and reduces with
pandas min, which skips missing observations. Direct deterministic witnesses:

| Supplied equity | Existing output |
|---|---|
| [100., NaN, 80.] | -0.19999999999999996 |
| nullable Float64 [100., pd.NA, 80.] | -0.19999999999999996 |
| [100., +Inf, 80.] | -1.0 |
| [100+2j, 80+3j] | -0.199720111955218, imaginary-discard warning |
| empty object Series | 0.0 |

These outputs do not certify the supplied complete real equity history. Missing
source equity is not an absent observation the routine is authorized to remove;
a complex curve is not a real wealth path. Independent research review confirmed
the witnesses. No RNG, vendor, broker or search is involved.

## Scope and limits

ADR-357 requires original real numeric nonboolean/noncomplex dtype and complete
finite native observations before empty handling. isna runs before isfinite.all
because nullable boolean reduction otherwise skips missing values. No float64
source conversion is introduced: a Series built from native longdouble array
['1e400','8e399'] has a measurable prior drawdown near -0.2 on the reviewed build.
The native wide array must precede Series construction to avoid already losing
source precision in pandas scalar-list inference.

Composed engine metrics already validate wealth, while lifecycle callers validate
raw returns; their extreme derived cumprod arithmetic remains a separate limitation.
No affected production position, false graduate, historical cohort or broker action
is established. The guard can refuse invalid derived equity downstream, so no
universal unchanged completion/denominator claim follows. Valid zero/negative
equity and existing derived warnings, NaN or exceptions remain outside this fix;
it does not promise finite drawdown for every finite numeric curve. Existing
numeric sparse cummax support is unchanged. All source operands and arithmetic,
thresholds, hashes, calibration identities and generated records remain.

## Verification

Before adoption, 63 native compatibility outputs/warnings/exceptions were frozen
at /tmp/qf-w43-s26-drawdown-source-baseline.json, SHA256
f9773bc78fb74f9246ab085b7cd6cf9dbf01d854ab41c14e3d97c8cab5c67084.
Actual preimplementation tests produced 61 failures and 19 passing controls in
3.69s, before metrics.py changed (`/tmp/qf-w43-s26-drawdown-red.log`). After the
patch, 591 focused tests passed in 14.66s. Independent final research review
approved all five paths and separately ran all 80 new tests, including exact
Fraction peak-ratio and missing-observation Hypothesis properties. Native and
nullable dtypes, wider finite inputs, malformed empties and source ownership
are covered without changing old tests.

Parent and independent AST audits found the entire prior metrics module
identical after removing exactly the two entry guards and restoring the prior
docstring. All 63 frozen outputs, warnings and exceptions replayed exactly,
including finite zero/negative equity and wider native observations. Source SHA256
dea9d12e93b57687060bf43945ed29289be5550201a0ebe223b03e0be95f9a26 remained fixed.

Fresh foreground `make check-all PYTEST_WORKERS=2` passed: 14,537 backend tests
(97.41% coverage), 731 frontend tests (97.88% statement coverage), lint, formatting
and type checks (`/tmp/qf-w43-s26-check357.log`). No generated data, frozen cohort,
threshold, policy hash or v14 identity changed.
