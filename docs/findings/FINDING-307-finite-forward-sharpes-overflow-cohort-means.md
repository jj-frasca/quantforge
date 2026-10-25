# FINDING-307: Finite forward Sharpes overflow cohort means

- **Status:** Corrected by ADR-367
- **Date:** 2026-10-24
- **Severity:** Medium — finite score evidence can publish a nonfinite summary
- **Scope:** `_mean_forward_sharpe` finite-input arithmetic
- **Prior art:** ADR-033, ADR-166, ADR-175 / FINDING-107, ADR-366

## Evidence and limits

Two valid positive-bar forward scores with Sharpe1e308 each produce an infinite
cohort mean through `sum(scored) / len(scored)`, although their mean is1e308.
The score and paper-position roots accept these finite statistics using supported
legacy empty curves/absent evidence. `DeflationCohorts` accepts the derived
infinity; its direct JSON serializer emits null, while FastAPI's
`jsonable_encoder` followed by Starlette `JSONResponse` locally raises a
noncompliant-float `ValueError`. This demonstrates incompatible transport, not
an observed full-route500 or affected current book. No real engine-generated
Sharpe1e308, false graduate, broker action or calibration effect is established.

The separate zero-bar inclusion defect is corrected by ADR-366. These witnesses
have positive bars and survive that filter. ADR-175 repairs analogous Monte Carlo
averaging only; it explicitly does not cover other summaries.

Mixed signs make a scaled fallback insufficient for this domain. Let M be the
largest finite float and s the smallest positive subnormal. On the reviewed
runtime, `[M,M,-M,-M,5*s]` has a nonfinite native sum; its exact represented mean
rounds to s, but scale-normalized averaging yields0. Moving the tiny term first
has the same result. `math.fsum` alone raises intermediate overflow. In contrast,
`[M,-M,5*s]` has a finite native result2*s that must stay unchanged.

## Correction

Preserve the selected sample, empty `None`, and every finite native result
exactly. Only when the native total is nonfinite, add the original finite builtin
float values as exact `Fraction.from_float` operands, divide the exact sum by the
count, then convert that rational mean to float once. Never convert the exact
sum before division, clip scores, discard extremes or normalize away small terms.

For a nonempty finite sample the exact mean lies between its finite operands;
its final rounded float stays in that finite range. Final rounding can legitimately
yield zero. This is exact arithmetic on represented source floats in a rare
fallback, not a claim that all finite native means are correctly rounded, that
the source Sharpe was measured accurately, or that unchecked model copies are
fully validated. Standalone manual summary construction remains outside this
producer correction. Counts, sample inclusion, formulas, schemas and thresholds
remain unchanged; no generated or frozen record is rewritten.

## Verification

The preimplementation run failed 19 regressions with 7 controls passing; the
focused suite then passed 80 tests, including 26 new cases and a Hypothesis
cancellation property against an independent integer-grid oracle. Session31
independently reviewed the inherited fix and replayed 152 exact native-finite
payloads and float encodings with caller nonmutation. A strict whole-module AST
comparison permits only the agreed helper suffix and two standard-library imports.
Fresh foreground `make check-all PYTEST_WORKERS=2` passed in session31, including
backend and frontend coverage gates. No source Sharpe accuracy or actual production
occurrence is inferred from these finite-input arithmetic controls.
