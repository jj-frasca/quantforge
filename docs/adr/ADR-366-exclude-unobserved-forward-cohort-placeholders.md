# ADR-366: Exclude unobserved forward cohort placeholders

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Codex autonomous session30, ISO2026-W43
- **Resolves:** FINDING-306
- **Extends:** ADR-033, ADR-166, ADR-361

## Context

Forward cohort means exclude absent scores but include zero-bar placeholders.
Replacing absence with a placeholder can halve a measured mean without adding
an observation. A zero-bar-only cohort reports zero instead of unmeasured.
This affects ordinary finite inputs; no extreme arithmetic is needed.

## Options considered

1. Require present scores to have positive forward bars for mean inclusion.
   This distinguishes unobserved placeholders from observed performance without
   changing cohort membership or the arithmetic estimator.
2. Filter by trade count. This would discard measured inherited-exposure returns
   with zero forward turnover, contradicting ADR-361.
3. Require126 bars. That is ADR-033's separate research re-evaluation trigger,
   not a minimum for this descriptive mean; imposing it would broaden scope.
4. Keep placeholder zeros. Unobserved data would continue to change performance
   while an equally unobserved absent score does not.

## Decision

Add only `and p.score.forward_bars > 0` to `_mean_forward_sharpe`'s existing
present-score inclusion predicate. Preserve all remaining executable statements.
No observed-bar scores means `None` through the existing empty-sample branch.

Keep membership counts, unknown-verdict handling, order and caller-selected
population unchanged. Include positive-bar zero-trade and zero-Sharpe scores,
one-bar samples and supported legacy empty curves/absent evidence. The statistic
remains an unweighted mean of per-position Sharpes, not a portfolio Sharpe or
an assertion that ADR-033's20-per-cohort/126-bar trigger has fired.

## Consequences and reversal

The API/CLI cohort means change only when zero-bar placeholders were included;
counts and stored scores remain. No financial formula, maturity threshold,
selection, lifecycle policy, schema, accounting-v14, generated record or frozen
cohort changes. Finite-sum overflow and broader arithmetic precision remain a
separate numerical issue, not silently repaired by this sample clarification.

Remove the added predicate to reverse this decision and reopen FINDING-306.
