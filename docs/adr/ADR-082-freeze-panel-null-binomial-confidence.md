# ADR-082: Freeze simultaneous confidence for panel-null tail probabilities

- **Status:** Accepted
- **Date:** 2026-09-06
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Acts on:** FINDING-018
- **Clarifies:** ADR-081

## Context

ADR-081 pre-registers 400 independent whole-panel null replicates, two fixed tail counts, a
plus-one two-sided Monte Carlo p-value, and an exact binomial confidence interval for each tail
probability. It does not freeze the interval's coverage, sidedness, or simultaneous-error policy.
Those are decision-relevant inputs because the result is called separated only when a tail interval
lies wholly below 0.025, not separated only when both lie wholly above 0.025, and unresolved
otherwise.

The construction must be chosen before any panel result exists. Selecting it after observing the
counts would violate ADR-081's protection against optional continuation and reinterpretation.

## Options considered

1. **Independent two-sided 95% Clopper–Pearson intervals.** Exact for either tail in isolation and
   conventional, but their joint coverage can fall below 95% while the decision reads both.
2. **One-sided intervals only in the direction used by the observed decision.** More powerful, but
   the direction and which bound matters would be selected after observing the counts unless every
   possible decision path were separately multiplicity-priced.
3. **Two two-sided 97.5% Clopper–Pearson intervals.** Conservative and exact; allocating 0.025
   noncoverage to each tail interval gives at least 95% simultaneous coverage by Bonferroni and
   publishes both bounds without a post-result choice.
4. **Normal or Wilson intervals.** Narrower and simple, but approximate at the extreme counts this
   experiment is explicitly designed to distinguish.

## Decision

Use option 3. For each of the lower- and upper-tail counts `k` out of `n = 400`, report a two-sided
97.5% Clopper–Pearson interval. Each bound uses `alpha / 2 = 0.0125`; the lower endpoint is zero at
`k = 0`, and the upper endpoint is one at `k = n`. Across the two reported tail intervals,
Bonferroni guarantees at least 95% simultaneous coverage. Preserve ADR-081's plus-one p-value,
0.025 tail threshold, and fixed three-way resolution exactly.

The inference implementation is pure and accepts only a complete validated
`PanelNullCalibration`. Walk-forward is always measured. Purged-CV inference is emitted only when
the real cohort statistic and every replicate statistic are present; partial secondary diagnostics
are reported as not measured, never filtered to a smaller post-hoc panel sample.

## Consequences

- The immutable panel sample has one deterministic interpretation before measurement.
- A tail count of 3/400 has an upper endpoint below 0.025; 4/400 does not. Boundary tests pin that
  distinction.
- Simultaneous coverage costs some resolution power relative to independent 95% intervals, which is
  accepted in exchange for avoiding an unpriced two-tail choice.
- No gate, validation threshold, production selection rule, generated artifact, or headline changes
  in this decision.

## Reversal

A different interval or coverage policy requires a new ADR before inspecting or extending a panel
measurement. Do not reinterpret a completed 400-replicate artifact under a newly selected interval.
