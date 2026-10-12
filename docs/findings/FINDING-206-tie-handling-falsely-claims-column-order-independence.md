# FINDING-206: Tie handling falsely claims column-order independence

- **Status:** Corrected — fixed-order tie convention disclosed
- **Date:** 2026-10-11
- **Severity:** Low — source-facing methodological guarantee is false
- **Scope:** long_short_weights documentation and repeatability-test comment
- **Decision:** ADR-257
- **Prior art:** ADR-024/140/149/252 ordered factor identity; FINDING-014 vectorization

## Evidence

Equal A/B/C/D signals at quantile 0.25 select A=-1 and D=+1. Reversing columns
and aligning back to the same names selects A=+1 and D=-1. Repeating the original
ordered input is exactly deterministic. Independent reproduction confirms both.
The docstring's claim of column-order independence and the test comment therefore
misstate what rank(method="first") and the repeatability assertion establish.

The ordered frozen universe retains this convention as part of the factor's
reconstruction identity. This finding does not establish a defective tie policy,
false graduate, bad book or calibration result. FINDING-037's PBO tie correction
concerns hypothesis-label invariance and is a different statistical boundary.
No search, cohort, workflow, broker or generated record was changed.

## Proposed correction and required evidence

ADR-257 corrects the docstring and test comment and documents fixed-order
determinism plus possible tied-name selection changes under reordering. Preserve
all executable code and test assertions. Capture and compare complete module ASTs
excluding actual docstrings; require independent final review and the full
foreground backend/frontend gate. No runtime behavior or RED claim is introduced.
Changing the algorithm needs a separate methodology decision and validation evidence.

## Verification

Complete executable panel AST and complete test AST are unchanged. Independent
review reproduced both tie-order examples and passed 79 existing panel/engine
tests. Foreground `make check-all` passed: 5,167 backend tests and 363 frontend
tests, with 97.78% backend and 97.63% frontend coverage. No runtime change or
new RED claim was needed for this documentation-only correction.
