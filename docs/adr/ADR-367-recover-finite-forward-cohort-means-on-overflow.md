# ADR-367: Recover finite forward cohort means on overflow

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Codex autonomous session30, ISO2026-W43
- **Resolves:** FINDING-307
- **Extends:** ADR-033, ADR-166, ADR-175, ADR-366

## Context

A finite sample can have a nonfinite intermediate sum but a finite arithmetic
mean. Two positive-bar scores with Sharpe1e308 produce infinity, which either
resembles missing evidence under direct model JSON or fails ordinary HTTP JSON
encoding. Severe mixed-sign cancellation also defeats normalized averaging;
the reviewed largest-float/subnormal witness loses a representable mean.

## Options considered

1. Preserve native finite results, with exact represented rational recovery only
   when their native total is nonfinite. This retains the estimator and ordinary
   rounding, at the cost of rare standard-library big-integer arithmetic.
2. Refuse the report. This avoids a nonfinite claim but discards a finite statistic.
3. Scale-normalize or divide every operand before addition. Small terms can be
   erased under cancellation or underflow, and ordinary results would change.
4. Replace sum with `math.fsum`. It can also raise intermediate overflow on the
   mixed-sign witnesses and is not sufficient by itself.
5. Clip or drop large scores. This changes the sample and estimator.

## Decision

Keep ADR-366's selected score list exactly. Preserve the empty `None` branch.
Compute the original native sum once; when finite, return its original division
by sample length. For a nonempty bounded Python list of validated finite floats,
finite total and finite native mean are equivalent.

Only for a nonfinite native total, sum `Fraction.from_float` values from exact
Fraction zero, divide that exact total by the integer sample length, and convert
the rational mean to float once. Do not convert the total to float before division.
Keep this local to `_mean_forward_sharpe`; add no shared numerical framework,
normalization, clipping, source conversion or new input-validation policy.

## Consequences and limits

The exact mean lies in the convex hull of finite source floats, so its final
rounded float is finite. Represented subnormal means survive intermediate
cancellation; a final result below float resolution may still round to zero.
Native finite inaccuracies and underflow remain intentionally unchanged. Normal
validated score roots supply builtin finite floats; this is not complete graph
revalidation or a new defense against arbitrary unchecked model copies.

Rare exact arithmetic allocates integers spanning the float exponent range;
no runtime benchmark or universal cost bound is claimed. None/membership counts,
unknown handling, positive-bar inclusion, zero-trade evidence, the unweighted
arithmetic estimator, schemas, thresholds, policy hashes, accounting-v14,
generated records and frozen cohorts remain unchanged. No actual production
report failure or engine-generated extreme score is established.

## Reversal

Restore the original conditional native mean and remove the two imports, while
retaining ADR-366's positive-bar filter. This reopens FINDING-307.
