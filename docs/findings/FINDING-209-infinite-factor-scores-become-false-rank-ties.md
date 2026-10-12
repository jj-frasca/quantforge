# FINDING-209: Infinite factor scores become false rank ties

- **Status:** Corrected — ADR-260 refuses infinite scores before ranking
- **Date:** 2026-10-12
- **Severity:** High — shipped factor arithmetic can select reversed legs
- **Scope:** Shared cross-sectional long_short_weights score boundary
- **Decision:** ADR-260

## Evidence

Use the shipped xs_momentum lookback=126/skip=0 configuration on 127 rows:
A=10**linspace(-200,200,127), B=10**linspace(-180,180,127). Append A=2e200,
B=1e180. Every supplied price is finite positive; every adjacent asset return is
finite. At row126 the true cumulative ratios are approximately 1e400 and 1e360,
with A larger, but both native scores overflow to infinity. Original supplied-order
ranking shorts A and longs B. The next published portfolio return is -1.0,
where exact-ratio ordering calls for the positive long-A return.

Independent research-expert review reproduced this shipped grid fixture and a
smaller analogous example. Signed infinities also pass direct ranking; reversal
can create negative infinite scores. This is not merely an arbitrary string-input
case. No historical cohort, graduate, calibration or broker contamination is inferred.

## Correction and required evidence

Refuse exact signed infinity before the shared rank operation, preserving original
quantile precedence, NaN missingness and every native valid rank/weight formula.
Do not introduce dtype bans, coerce scores, drop names or recover factor arithmetic.
Independent scope probes preserve finite longdouble extrema, huge Fraction/Decimal,
nullable scores, bool, missing and empty frames. Observe RED before production,
verify exact valid baselines and all generators, then complete the foreground gate.
Finite-score precision and generators that erase overflow remain separate limitations.

## Observed verification

Pre-implementation tests recorded 19 failures and six preserved native cases.
The two-line guard passed 327 affected engine/ranker/forward/search tests.
Independent final review approved 155 engine/ranker tests, 19 exact supported
native rank baselines and 45 configurations across all 16 standard generators.
Inputs and NumPy error state remain intact; malformed quantile precedence and
refusal before ranking were independently checked. Exact Fraction ratios of the
original float observations verify the shipped fixture's true score ordering.
The pre-existing pandas finite-wide ranking cast warning remains; this guard
does not certify the precision of finite scores or suppress native warnings.

Fresh foreground `make check-all PYTEST_WORKERS=4` passed: 5,243 backend tests
at 97.75% coverage and 363 frontend tests at 97.63% statement coverage; lint,
formatting and type checks passed.
