# ADR-290: Anchor accepted Float64 Sharpe dispersion when translation is exact

- **Status:** Accepted
- **Date:** 2026-10-14
- **Deciders:** Codex autonomous session 11, ISO 2026-W42
- **Resolves:** FINDING-239
- **Extends:** ADR-203, ADR-209, ADR-286, ADR-044

## Context

Positive finite native standard deviation does not certify represented-sample
variance. For three consecutive Float64 values beginning at 1e-100, native
centering accepts annualized Sharpe 7.911860051945091e16 versus exact represented
sample 1.2509749146322299e17. There is no underflow, so ADR-286 deliberately does
not correct it. The rounded mean used for centering can inflate variance even
when the numerator remains accurate to normal floating precision.

## Options considered

1. Correct the native-accepted branch only when exact translation is certified
   by the same-sign factor-two range: selected, inexpensive and bounded.
2. Replace every Float64 estimate with exact rational moments: greater scope,
   CPU cost and range/rounding complexity than the demonstrated defect needs.
3. Use a closeness epsilon or sample-count heuristic: arbitrary and unnecessary.
4. Keep finite native dispersion: preserves reproduced false measurement.

## Decision

After original source validation, short/exact-constant checks and native arithmetic,
only for original native float64/classic nullable Float64 whose nonzero native mean,
positive STD and annualized score were accepted without detected underflow, use
anchored dispersion when every observation is strictly positive or strictly
negative and max(abs(values)) <= 2*min(abs(values)). Power-of-two multiplication is exact when representable; if twice the
minimum overflows, its exact value exceeds the largest Float64 and therefore
every finite maximum. This is an exact-subtraction certificate, not a risk threshold: by the
binary Sterbenz relation, every subtraction of the first observation is exact.
The factor-two boundary is inclusive; values just outside retain their prior path.
The subtraction relation is verified against David Goldberg (1991),
[What Every Computer Scientist Should Know About Floating-Point Arithmetic,
Theorem 11](https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html);
IEEE binary64 supports gradual subnormal representation. Exact Fraction difference
checks independently protect the implemented boundary.

Normalize these represented differences by their maximum magnitude and compute
the same ddof=1 sample STD. Preserve the already accepted native mean, separate its
mantissa/exponent from the difference scale, evaluate the annualized ratio with
normalized STD, then restore one exponent difference. Do not substitute fsum: retain the actual
accepted native numerator and its original aggregation contract.
Require a finite final score or the existing ValueError. Validation/constant
precedence, caller observations and NumPy state remain. O(n) time/memory, no new
dependency, cache, risk floor or ratio cap.

Normalized differences include zero and unit magnitude. Their sample STD lies
between 1/sqrt(2*(n-1)) and sqrt(2), bounding the mantissa ratio within feasible
array ranges. Selected nearconstant and ordinary oracles use exact represented
Fraction variance with the actual accepted native mean, plus agreeing Decimal
200/800. This does not certify arbitrary native numerator accuracy or universal
correct rounding. Mixed-sign, zero-containing, wider-spread, other dtype and
nonfinite/underflow/mean-ratio failure paths retain their exact prior behavior.
Existing ADR-286 recovery remains unchanged. Primary Sharpe and its derived iid confidence interval can change; the interval
formula and assumptions stay. Other metrics including descriptive volatility
keep their separate contracts.

Advance accounting to
`whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-anchored-dispersion-pbo-exact-translation-sharpe-exact-translation-v13`.
Historical v12/v11 and frozen v10 measurements retain executed attribution and cannot
certify v13. Current v13 null/power/heavy-tail/bootstrap distributions are
unmeasured. Do not rerun, redraw, pool or relabel frozen cohorts. No threshold,
selector, catalog, grid, budget, schema or generated-data changes.

## Verification

Independent read-only scope approved 280 Fraction/Decimal signed nearconstant
and ordinary cases, exact subtraction identities, 207 exact outside/failure
controls, factor-two endpoints and extreme represented range. 100k public
prototype approximately .0036s. Require ADR-first/public genuine RED, Hypothesis,
source/failure/boundary controls, v12 restoration and v13 identity, exact outside
and other-field preservation, independent final review, foreground make check-all
and exact pushed CI. No actual false graduate or market contamination established.

## Reversal

Restore native-accepted Sharpe and v12 identity together, keeping ADR-289 PBO; retain the written
finding and historical calibration attribution. This reopens FINDING-239.
