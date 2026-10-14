# ADR-291: Certify Float64 OOS dispersion before selection and scoring

- **Status:** Accepted
- **Date:** 2026-10-14
- **Deciders:** Codex autonomous session 12, ISO 2026-W42
- **Resolves:** FINDING-240
- **Extends:** ADR-038, ADR-039, ADR-199, ADR-202, ADR-248, ADR-044
- **Relates to:** ADR-289, ADR-290

## Context

Both public OOS evaluators select config 1 on the frozen F240 matrix although
exact represented sample variance ranks config 0 first. Positive finite native
STD alone does not certify variance when centering uses a rounded mean. Correcting
PBO and primary Sharpe does not correct these independent NumPy scalar kernels.
The geometry is valid; this finding establishes numerical selection error, not
look-ahead leakage or an actual false graduate.

## Options Considered

1. Anchor dispersion only within the certified exact-subtraction domain.
   Pro: small, independently testable correction with bounded arithmetic.
   Con: ordinary eligible scores can change rounding; other precision gaps remain.
2. Use exact rational moments on every accepted sample.
   Pro: broader represented variance control. Con: broader estimator/CPU scope,
   additional rounding/range policy beyond the reproduced defect.
3. Reuse primary pandas Sharpe or vectorized PBO scores.
   Pro: fewer algorithms. Con: changes native numerator/layout or refusal policy,
   whereas these scalar diagnostics have distinct established contracts.
4. Keep native finite moments.
   Pro: no code change. Con: retains demonstrated wrong config selection.

## Decision

Keep both scalar helpers' original singleton/exact-constant shortcuts and native
STD, mean, annualization order, finite/positive guards and ValueError precedence.
Only after all native guards pass, and only for original represented Float64
sources (dtype kind f, itemsize 8, including byte order and complete masked
containers), permit a shared private NumPy translation helper. Carry separate
original matrix and benchmark provenance flags through float64 materialization;
pass the matrix flag to every training/selected-test score and benchmark flag to
every kept test control. Numeric lists retain their inferred source dtype.
Other source families always retain the prior kernel result.

A nonzero accepted native mean and strictly same-sign observations with
maxabs <= 2*minabs certify exact first-observation subtraction by the binary
Sterbenz relation. The boundary is inclusive; overflowing twice-minimum is a
valid bound on finite maxima. See David Goldberg (1991),
[What Every Computer Scientist Should Know About Floating-Point Arithmetic,
Theorem 11](https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html).
Normalize these exact differences by their maximum magnitude and compute the
same NumPy ddof=1 STD. Preserve the actual already accepted native mean, separate
mean and difference-scale mantissas/exponents, annualize the mantissa ratio and
restore one exponent difference. Require finite final score with the existing
ValueError. The normalized sample includes zero and unit magnitude, bounding
STD between 1/sqrt(2*(n-1)) and sqrt(2) for feasible array sizes.

Mixed-sign, zero-containing, outside-factor-two and native-zero-mean blocks keep
exact prior scores. Native zero/nonfinite STD, nonfinite mean or nonfinite native
annualized score still refuses before translation; no recovery is added. Existing
ignore-underflow policy stays: finite positive partial-underflow STD may be
corrected. Caller NumPy state and source observations remain unchanged.

All geometry, split/fold order, first-index argmax ties, embargo, dropped folds,
benchmark pairing, aggregation, result schemas and diagnostic status remain.
Corrected rounded scores do not promise exact ranking for arbitrarily close ties
or arbitrary native numerator accuracy. O(n) time/memory per eligible block;
primary Sharpe, PBO and descriptive metrics keep their independent contracts.

Advance accounting to
`whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-anchored-dispersion-pbo-exact-translation-sharpe-exact-translation-oos-exact-translation-v14`.
Stored diagnostics and the nondefault walk-forward family selector can change;
historical v13/v12/v11 and frozen v10 measurements retain executed attribution
and cannot certify v14. Current v14 null/power/heavy-tail/bootstrap distributions
are unmeasured. No frozen cohort rerun/redraw/pooling/relabeling, dispatch,
threshold, selector rule, catalog, budget or generated-record change.

## Verification and consequences

Independent read-only scope approved 140 signed nearconstant/ordinary
Fraction variance with agreeing Decimal200/800 known-native-mean oracles,
192 exact subtraction endpoints and the corrected frozen public selection.
Public tests must fail before implementation, cover independent source flags,
exact outside/refusal controls, Hypothesis, native numerator ownership and
historical v13 restoration/current v14 identity. Require independent final
review, full foreground make check-all, explicit-path commit and exact CI.
Eligible scores and selected configs can change intentionally; no actual
production graduate or historical-calibration impact is established.

## Reversal

Remove translated OOS scoring/source flags and restore v13 accounting together,
retaining primary ADR-290 and PBO ADR-289. Preserve F240 and historical attribution;
this reopens the demonstrated numerical selection error.
