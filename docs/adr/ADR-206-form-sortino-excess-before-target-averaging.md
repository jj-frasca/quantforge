# ADR-206: Form Sortino excess before target averaging

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 15, ISO 2026-W41
- **Resolves:** FINDING-146, FINDING-147
- **Extends:** ADR-187, ADR-205

## Context

Subtracting a nonzero target after averaging can lose representable excess in
both finite native arithmetic and ADR-205 recovery. Narrow float32 comparisons
can also round away a real shortfall relative to a float64 target. These are
mathematical evidence errors, not an unrepresentable score.

## Options considered

1. Form individual float64 excess before mean and recovery: selected.
2. Preserve every finite native nonzero-target result: retains documented errors.
3. Use Decimal for every metric: unnecessary runtime/dependency cost; independent
   Decimal remains the verification oracle.

## Decision

After unchanged target/source validation and singleton precedence, compare the
validated float64 values directly with target to establish no downside. Form
individual float64 excess once. For nonzero targets use pandas mean of those
excesses, rather than subtracting target after a rounded return mean. For target
zero retain the original pandas return mean exactly, including nullable numeric
estimator behavior. Native full-sample downside and annualization order remain.

On failed native arithmetic, normalize finite individual excesses by their own
maxabs. Only if excess subtraction is nonfinite normalize original source and
target together before subtracting. Normalize the resulting excess for stable
summation with math.fsum, then use ADR-205's separate shortfall scale and original
full-sample denominator. Keep required nullable representation for unmeasurable
ratios and measured short/no-downside zero. No score cap or target bound.

## Verification and limits

RED exact-float Decimal tests precede correction: signed adjacent ordinary/huge
targets, float32/nullable Float32 shortfalls, nonzero-target negative/positive
scores. Hypothesis nonzero-target oracle over a fixed binary excess grid and exact native target-zero
compatibility protect the definitions. Full-domain engine properties remain.

FINDING-148 separately records finite native mean underflow. This change addresses
target cancellation and narrow comparison, not arbitrary finite precision.
Normalization/subtraction rounding and partial moment underflow remain possible;
fsum cannot restore information already lost before summation. A ratio rounding
below the smallest subnormal can legitimately be measured zero. Sortino is
strictly descriptive: accounting identity v9, thresholds and generated evidence
remain unchanged; no calibration dispatch.

## Reversal

Restore ADR-205 mean-minus-target and Series comparison. This reopens both findings.
