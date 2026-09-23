# ADR-105: Make PBO tie handling permutation-invariant

- **Status:** Accepted
- **Date:** 2026-09-22
- **Deciders:** Codex autonomous session 6 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-037
- **Extends:** ADR-036, ADR-044, ADR-104

## Context

CSCV defines PBO from the out-of-sample rank of the in-sample-best configuration. The published
procedure assumes ranks identify that selection, but finite discrete strategy grids can produce
exact Sharpe ties. FINDING-037 shows that NumPy's positional tie behavior makes the current result
depend on candidate column order and can move an unchanged matrix across the live 0.5 gate.

The implementation needs an explicit tie extension. Column position cannot choose evidence, and
breaking a tie with out-of-sample performance would leak the quantity being measured back into
selection.

## Decision

For every CSCV split:

1. identify every configuration tied at the maximum in-sample Sharpe;
2. assign out-of-sample Sharpes their average one-based rank, so an equal-valued block occupies the
   midpoint of the ranks it spans;
3. compute the ordinary CSCV logit for each tied in-sample winner; and
4. contribute the mean of those winners' `logit <= 0` indicators to the split's overfit count.

The final PBO remains the mean across CSCV splits and remains in `[0, 1]`. With no ties this is
byte-equivalent to the existing procedure. With ties it is the expectation under uniform random
selection among statistically indistinguishable in-sample maxima, without using out-of-sample
values to choose one.

`pbo_max` remains strictly 0.5. The calibration accounting-method identity advances because tie
handling is part of the measured procedure. Existing artifacts remain evidence for their recorded
identity; this decision does not dispatch replacements or edit generated data.

## Alternatives considered

- **Keep the first in-sample maximum.** Rejected: candidate position then changes a live gate.
- **Use a stable sort for OOS ties.** Rejected: stability makes the result reproducible for one
  order, not invariant to a different order.
- **Choose the best or worst OOS member of an IS tie.** Rejected: both leak OOS information into
  the selection and bias the statistic deliberately.
- **Add tiny random jitter.** Rejected: it makes a deterministic gate seed-dependent and invents
  distinctions absent from the returns.

## Consequences

- Candidate-label permutations cannot change PBO, including in degenerate flat/discrete grids.
- Split contributions may be fractional when several IS winners straddle the OOS median; PBO was
  already a probability and requires no schema change.
- No-tie production cases are unchanged. Calibration identity prevents old tie semantics from
  being silently pooled with the corrected procedure.

## Reversal

Restore positional `argmax` and ordinal double-`argsort` ranking. That would restore the
cross-threshold order dependence documented in FINDING-037 and is not recommended.
