# FINDING-308: Finite pool diagnostics overflow summaries

- **Status:** Corrected by ADR-368
- **Date:** 2026-10-25
- **Severity:** Medium — finite diagnostic evidence can publish nonfinite summaries
- **Scope:** `pool_report._summarize` median and linear p95
- **Prior art:** ADR-051, ADR-079, ADR-162, ADR-217 / FINDING-166

## Evidence and limits

Ordinarily constructed `Trial` roots accept finite walk-forward and purged-CV
diagnostics. For either field, two values of `1e308` produce an infinite median
in `_summarize`. The pair `[-sys.float_info.max, sys.float_info.max]` produces
a p95 of negative infinity, below both inputs, although its exact linear p95 is
finite and lies within the sample range. Independent review reproduced all four
field/input combinations. The model serializer emits null for the nonfinite
summary; local FastAPI encoding followed by Starlette `JSONResponse` raises a
noncompliant-float `ValueError`. NumPy overflow/invalid raise policies can also
raise before a summary is constructed.

These are finite-input boundary witnesses, not an observed current pool failure,
full-route 500, engine-generated extreme diagnostic, false graduate or changed
gate. The summary's existing trial population and missing-score filter are not
the defect. FINDING-166 identified the same NumPy endpoint overflow in calibration
summaries; ADR-217 explicitly left other report consumers outside its correction.

## Correction

Delegate this producer's numerical summary to the existing ADR-217 `_percentiles`
helper. It preserves finite native median/p95 answers and the maximum; only
nonfinite median/p95 arithmetic invokes exact rational endpoint interpolation
at the existing binary virtual index. Local NumPy error handling preserves the
caller's policy. Empty samples remain None, and present invalid inputs refuse
through the helper's existing finite-real guard rather than being discarded.

Keep selected trials, nullable filtering, counts, fields and the linear estimator
unchanged. This does not revalidate unchecked Trial graphs, certify arbitrary
finite-native precision, or repair the other reducers in `pool_report`. No
threshold, search identity, accounting-v14, generated record or frozen cohort
changes are needed.

## Verification

The preimplementation run failed 35 regressions with 10 controls passing.
The focused suite then passed 181 tests, including 45 new cases covering both
fields, NumPy ignore/warn/raise policies, public finalist-summary JSON transport,
missing/singleton/native controls and a Hypothesis convex-range property with
an independent integer-grid interpolation oracle.

Independent review approved all six paths, replayed 88 exact native-finite
payloads and float encodings with unchanged caller Trials, and verified the
whole module AST differs only by the helper import and agreed numerical suffix.
Fresh foreground `make check-all PYTEST_WORKERS=2` passed 14,746 backend and
746 frontend tests, including lint, formatting, strict typing and coverage gates.
These controls establish this producer correction without certifying other
reducers, source diagnostic accuracy or any affected production record.
