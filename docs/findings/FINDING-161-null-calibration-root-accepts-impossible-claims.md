# FINDING-161: Null-calibration root accepts impossible claims

- **Date:** 2026-10-08
- **Severity:** High — durable Type-I evidence validity
- **Status:** Resolved under ADR-215
- **Reproduced revision:** `e0980b0f`

The legacy-compatible `NullCalibration` root accepts zero searched symbols,
negative graduate/survivor counts, false-graduation rate 2, infinite deflation
bar/maximum DSR, and NaN maximum holdout Sharpe. An infinite maximum DSR
survives `merge_calibrations` reconstruction. It also accepts a claimed
graduate absent from its graduate list and survivors exceeding graduates.
Leaf validity and immutability do not establish these root contracts.

These are constructed malformed-evidence reproductions, not an observed
incorrect production result. All eight committed null artifacts have positive
searched counts, ordered nonnegative counts, graduate-list count agreement
and exact rate/count agreement. No artifact is modified.

The bounded correction requires original integral nonboolean counts (positive
searched, nonnegative graduate/survivor), finite real nonboolean root scores,
original rate within [0,1], nonnegative deflation bar, and count/list/rate
agreement. Preserve signed finite maxima, nullable unmeasured holdout maxima,
legacy optional arrays and valid numeric scalars. No dropping, clamping,
invented counts, changed thresholds or generated-data writes.

This does not certify legacy diagnostic arrays, root maximum recomputation,
the deflation-bar formula, symbol identity or all downstream arithmetic.

## Correction and verification

ADR-215 establishes the bounded root contracts above. Initial tests observed
43 RED and five preserved cases before implementation. Expanded original-value
cases were replayed against committed `e0980b0f` code loaded only into an
exclusive scratch module: 56 RED and five preserved cases. The exact-Fraction
upper-rate case has a coherent full-graduation payload so float rounding cannot
hide behind an unrelated count mismatch.

Independent research review approved the correction and validated all eight
committed artifacts read-only. Final root/consolidation tests passed 64 cases;
all 18 offline endpoint tests passed. Existing fixtures were made coherent:
missing history now has a positive searched denominator, and claimed graduates
now have records. Their missing-history and API assertions were preserved.
Full mandatory foreground `make check-all PYTEST_WORKERS=4` passed 3,318
backend tests (97.54% coverage) and 359 frontend tests (97.63% statements).
