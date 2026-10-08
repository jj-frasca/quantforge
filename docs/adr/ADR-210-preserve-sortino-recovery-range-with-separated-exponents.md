# ADR-210: Preserve Sortino recovery range with separated exponents

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 15, ISO 2026-W41
- **Resolves:** FINDING-152
- **Extends:** ADR-205, ADR-206, ADR-207

## Context

F152 shows that mean-first division in normalized Sortino recovery erases a
representable subnormal ratio. Simply annualizing first or dividing the downside
scale earlier can move the problem: a tiny downside can overflow an intermediate
quotient that sample-count division would make finite.

## Decision

Retain source/target validation, float64 shortfall comparison, short/no-downside
zero conventions, native measurability policy and required nullable result.
Only recovery changes. Compute stable normalized excess sum with math.fsum.
A zero stable sum gives measured zero. Otherwise separate its mantissa/exponent
and the positive downside scale with math.frexp. Evaluate the bounded mantissa
ratio `sqrt(252) * sum_mantissa / rms / n / downside_mantissa`, then apply the
exponent difference once with math.ldexp. OverflowError or nonfinite final score
returns None; valid subnormal rounding, including genuine tiny zero, remains.

The downside normalization has at least one observation of magnitude one, so
`rms >= 1/sqrt(n)`. Both frexp magnitudes are in [0.5, 1); for feasible arrays
the mantissa calculation stays representable. This avoids intermediate range
failures without changing the full-sample ratio or introducing an estimator.

Common-scale normalization can itself erase tiny observations before stable
summation; this remains an explicit limitation, not a universal precision claim.
No native measurable score changes are intended. Sortino remains descriptive;
calibration identity v10, all gate thresholds and generated evidence stay.
No workflow dispatch or paid resource.

## Verification

Signed/permuted smallest-subnormal residuals with 3/100 observations fail before
code, then match independent exact-float Decimal800 oracles. Protect finite
near-max results against premature overflow, true ratio overflow as None, genuine
cancellation/tiny zero and original native compatibility. Hypothesis covers binary
scaled cancellation residuals across the representable subnormal boundary; retain
all existing engine financial property domains. Independent research review and
full foreground make check-all precede individual delivery.

## Reversal

Restore normalized mean-first recovery and sequential unscaled quotient evaluation.
This reopens F152.
