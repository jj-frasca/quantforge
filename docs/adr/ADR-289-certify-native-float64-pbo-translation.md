# ADR-289: Certify exact translation before correcting native Float64 PBO dispersion

- **Status:** Accepted
- **Date:** 2026-10-14
- **Deciders:** Codex autonomous session 11, ISO 2026-W42
- **Resolves:** FINDING-238
- **Extends:** ADR-104, ADR-105, ADR-106, ADR-189, ADR-200, ADR-201, ADR-044

## Context

Rounded native centering can inflate represented sample variance while every
moment remains finite. FINDING-238 freezes an eight-row two-config Float64 matrix
whose public CSCV PBO is 1/3, versus 2/3 under exact represented variance, crossing
the unchanged strict 0.5 live gate. Anchored dispersion with the same native
means reproduces 2/3. One balanced split chooses the wrong IS winner and another
reverses its OOS rank. This is direct synthetic evidence, not a false graduate
or a measured market/null-calibration outcome.

## Options considered

1. Correct native accepted Float64 columns only under an exact subtraction
   certificate, retaining the original means and all prior refusals: selected.
2. Replace every input family or use exact rational rankings: greater scope and
   CPU/rounding complexity than the reproduced defect requires.
3. Use an epsilon/nearconstant heuristic: arbitrary and unnecessary.
4. Keep native finite variance: retains the cross-threshold false pass.

## Decision

Keep original shape/dtype/mask/finite/history checks and float64 materialization.
Carry original real-floating eight-byte provenance through the subset cache to
_sharpe_per_config with an explicit exact_translation boolean. Other original
integer/narrow/wider inputs retain their prior scoring. The private FloatArray
helper defaults true; the public boundary supplies the original source flag.

Identify exact constants and compute native full-block mean/STD and quotients on
the unchanged original layout. Execute all existing nonconstant measurability
and final-finite guards before correction. For original Float64 only, correct
nonconstant native-accepted columns with nonzero native mean whose observations
are strictly one sign
and maxabs<=2*minabs. The inclusive factor-two relation certifies each represented
subtraction of the first observation as exact; no validation threshold moves.
This relation is verified against David Goldberg (1991),
[What Every Computer Scientist Should Know About Floating-Point Arithmetic,
Theorem 11](https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html).
Power-of-two doubling is exact when representable. If twice the minimum
overflows upward, its exact value exceeds the largest Float64, certifying the
comparison against every finite maximum. Original observations and gradual
subnormal representation are retained.

Normalize those represented differences by their own maxabs and calculate sample
STD (ddof=1). Preserve the already computed full-block native means. Form per-bar
mean/STD ratios from separated mean/scale mantissas and one exponent difference,
without encoding an intermediate unscaled STD. Require finite final quotients
through the original error. Constants, original source/refusal precedence,
noneligible columns, CSCV geometry, cache, ties/average ranks and strict pbo_max
are unchanged. Original caller arrays and NumPy state remain. No imputation,
filtering, floor, cap, random jitter or new dependency.

PBO's existing underflow-ignore policy remains: eligible finite positive native
STD can include partial square underflow; zero/nonfinite native STD still refuses
before correction. Normalized differences include zero and unit magnitude, so
STD lies in [1/sqrt(2*(n-1)),sqrt(2)]. Its separated mantissa quotient stays bounded
for feasible arrays. Selected variance oracles use exact represented Fraction
moments with actual native means; arbitrary numerator accuracy and universal
correctly rounded/ranked ties are not certified. Original other families and
mixed-sign, zero-containing or wider-spread native columns retain prior results.
Primary Sharpe, diagnostics and descriptive volatility are separate limitations
and are not corrected here.

Advance accounting to
`whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-anchored-dispersion-pbo-exact-translation-v12`.
Historical v11 and frozen v10 evidence keep executed attribution; current v12
null/power/heavy-tail/bootstrap distributions are unmeasured. Do not rerun,
redraw, pool or relabel frozen cohorts. No threshold, selector, grid, budget,
schema, generated-data or workflow changes.

## Verification and cost

Require public test-first RED, exact per-split ranks, signed/transposed-layout
and permutation/tie/constant controls, Hypothesis known-native-mean variance,
original source flag propagation, failure/mask precedence, old v11 restoration,
independent exact outside review, foreground make check-all and exact pushed CI.
Independent realistic 7400x200/70-subset prototype .176-.181s native versus
.212-.213s proposed (about 20% overhead); all-eligible adversarial panels1.153s.
O(n*k) time/memory per eligible subset; no mutable cross-call caches.

## Reversal

Restore native PBO scoring and v11 accounting together, retaining the written
finding, historical evidence and the unchanged strict gate threshold.
