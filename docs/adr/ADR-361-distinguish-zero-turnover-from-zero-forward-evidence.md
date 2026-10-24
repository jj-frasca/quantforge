# ADR-361: Distinguish zero turnover from absent forward return evidence

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Codex autonomous session 29, ISO 2026-W43
- **Extends:** ADR-020, ADR-073, ADR-168, ADR-356
- **Resolves:** FINDING-301
- **Supersedes:** ADR-073's unconditional zero-forward-trade inference

## Context

Forward turnover can be zero while a warmed strategy remains exposed throughout
the post-freeze sample. The default built-in MomentumStrategy can remain long,
earn a first forward return of -35%, and have no forward position changes. The
current lifecycle skips its 25% risk limit and reports unmeasured zero statistics.
The forward score also suppresses the benchmark comparison for a zero-turnover
strategy even when its return path is nonzero. No production occurrence is claimed.

## Options Considered

1. **Retain the no-evidence exemption only for zero trades and all-zero returns.**
   - Pro: uses already available original evidence and preserves actual counts,
     thresholds and genuinely inactive behavior without changing persisted shape.
   - Con: all-zero net returns still cannot distinguish flat exposure from
     exposure earning exactly zero; return evidence does not attest execution.
2. **Add exposure counts or invent an entry at the freeze boundary.**
   - Pro: explicit exposure metadata could distinguish some zero-return cases.
   - Con: expands stored/API contracts or fabricates execution and changes entry
     costs; neither is needed to classify the demonstrated measured returns.
3. **Remove every no-trade exemption.**
   - Pro: eliminates this bypass.
   - Con: reintroduces ADR-073's manufactured Sharpe failures for inactive paths.

## Decision

After existing validation and grace, use the single-name no-evidence branch only
when the original forward trade count is zero and every original validated
forward return equals zero. Test per-observation inequality with zero, without
an epsilon, sum/product shortcut or numeric projection. Nonzero returns with
zero turnover go through the identical existing drawdown, rolling metrics and
predicates. In evaluate_forward, permit the unchanged strict Sharpe comparison
when there is at least one forward turnover event OR at least one nonzero forward
return. Preserve the actual count of zero; never manufacture a trade.

Keep grace, genuinely all-zero/no-trade holds/timeouts, defaults, policy hashes,
all threshold comparisons/reasons, original arithmetic, score/curve schemas,
cross-sectional behavior, account/broker execution and accounting-v14 unchanged.
Historical data and decisions are not rewritten. Accepted ADR-073 remains intact;
only its inference that zero turnover proves absent return evidence is superseded.

## Consequences and verification

Inherited exposure with measured returns now faces existing risk/performance
rules and can report its actual benchmark comparison. This is evidence
classification, not independent edge validation or an executable-account policy.
Zero-return exposure and entry/switching-cost reconciliation remain outside scope.

Observe actual RED on new pure and public-engine/public-dataset witnesses before
implementation. Preserve the two ADR-356 zero-count loss scenarios, updating their
assertions to require measured risk instead of the now-refuted exemption; delete
or skip no tests. Include exact-zero/signed-zero/native-small values, grace,
timeout, offsetting returns and Hypothesis drawdown/evidence invariants. Confirm
ordinary nonzero-count output preservation and unchanged inactive paths, required
independent research review, focused/full foreground gates and exact master CI.

## Reversal

Restore the two original trade-count-only conditions. That reopens FINDING-301.
