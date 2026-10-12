# FINDING-215: IC summaries accept impossible original coefficients

- **Status:** Corrected — derived endpoints and original summary evidence guarded by ADR-266
- **Date:** 2026-10-12
- **Severity:** High for direct public summary evidence
- **Scope:** summarize_ic original observations and derived rank_ic endpoint range
- **Decision:** ADR-266

## Evidence

summarize_ic([2,3]) publishes finite mean=2.5, although an IC is a correlation.
[2,-2] even produces a superficially bounded mean despite invalid component
observations. NaN/infinity can publish nonfinite statistics, and malformed singletons
return None before any observation check. Complex/string encodings are silently
coerced by float conversion. Native Fraction/Decimal/wide values just beyond one
can round into float64 one, so checks after conversion cannot validate original evidence.

Independent review also found why a summary-only strict bound is insufficient:
perfect centered-rank correlation at 21 tested universe sizes from 2..100 emits
1.0000000000000002. Exact Cauchy-Schwarz bounds the coefficient; this is endpoint
roundoff from the norm product, not invalid original rank evidence. N=17 reproduces
it with finite ordinary prices and signals. No historical contamination is inferred.

## Correction and required evidence

Require finite defined derived IC before endpoint projection, then validate original
summary scalars as finite real coefficients in [-1,1] before conversion/count shortcuts.
Never clip raw observations, drop missing cells or relax bounds to hide invalid source.
Preserve valid native bool/Fraction/Decimal/wide values and original summary formulas,
including the deliberate std floor. Broader model-leaf or summary-precision rules stay
separate. The native scalar helper is reused without changing cost behavior.

Independent pre-code review approved 19 signed invalid singleton probes (including
native endpoint neighbors), seven preserved numeric/floor/short/empty summaries,
legitimate perfect derived endpoints and exact series/summary fixtures across 16
generators/45 configurations. Valid derived endpoints can change an ULP, including
production; no unchanged-everywhere claim or generated-data relabeling is made.
Longitudinal calibration identity and all graduation thresholds remain unchanged.

## Observed verification

Initial pre-implementation RED recorded 40 failures and 20 preserved cases.
Review then found two negative Decimal fixtures had rounded to the valid endpoint
through context-dependent unary negation. Exact copy_negate and native outside-
bound assertions corrected the fixtures without changing production code. Three
corrected Decimal cases failed against an isolated original published implementation
before the final affected run passed 535 tests. No test was skipped or deleted.

Independent final review approved 135 IC tests, original native endpoint guards,
ten exact accepted/floor baselines, bounded perfect/inverted panels across sizes
2..100 (21 original endpoint overshoots corrected), unchanged series and summaries
across 16 generators/45 configurations, and refusal of injected nonfinite derived
evidence before projection. Caller state and parent AST restoration were verified.

The complete foreground make check-all passed 5,438 backend tests and 363 frontend
tests, with coverage 97.73% and 97.63%, respectively. All verification closed.
