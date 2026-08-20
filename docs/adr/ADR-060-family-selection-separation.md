# ADR-060: Report whether the search's choice of strategy family is separable from noise

- **Status**: Accepted
- **Date**: 2026-08-20
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-058 §Decision 3 (the next unit is the selection step), ADR-059 (capture per category)
- **Relates to**: ADR-043 (Sharpe standard error / detectable-edge frontier), ADR-033 (pool report)

## Context

ADR-059 measures, on planted data, whether the strategy that won a search was even trading the
planted process. The same question on **real** data has never been asked, and the pool already
contains everything needed to answer it: 3,237 experiments, each carrying one finalist per strategy
family.

Computed over the current pool (2026-08-20, 34-strategy catalog):

| category | median best-in-category in-sample Sharpe | share of max-DSR wins |
|---|---|---|
| Trend | +0.585 | 27% |
| Mean Reversion | +0.567 | 52% |
| Breakout | +0.530 | 15% |
| Combination | +0.405 | 6% |

**The median gap between the winning category and the runner-up is +0.079 Sharpe.** Lo (2002)'s
standard error for a Sharpe near zero over the ~21-year history these rows were searched on is
≈ 0.22. The gap is roughly **a third of one standard error**.

That is a fact about this project's own output, and it is not visible anywhere: a pool row records
`best_strategy_name` with no indication of how far ahead of the alternatives it was. Every place the
project speaks about "what the search finds" — the leaderboard, the pool report, ADR-045's capture
reading — implicitly treats the selected family as informative. On this evidence, for a typical
symbol, it is not.

This does **not** say the gate is broken or the pipeline is wrong: the gate graduates almost nothing
and the deflation bar is doing its job. It says the *intermediate* label the search attaches is
weaker than it looks, which matters because the capture reading and the strategy-design backlog are
both built on it.

## Decision

**Add `PoolReport.category_separation`, and state the verdict in the same breath as the number.**

1. `CategorySeparation` carries: `medians` (median best-in-category in-sample Sharpe per category),
   `winner_shares` (share of experiments whose max-DSR finalist came from each category),
   `median_gap` (median over experiments of best category minus runner-up), `standard_error` (Lo's
   SE at the pool's own `median_n_bars`, `None` when the pool does not state its history), and
   `separable` (`median_gap > standard_error`, `None` when the SE is unknown).
2. `separable` is `None` — not `False` — when the history is unknown. Every pool row written before
   ADR-052's amendment is in that state, and "not measured" must never render as "not separable".
3. `scripts/pool_report.py` prints the table and the verdict sentence.

**The SE is Lo's, at the pool's own history length**, the same scale ADR-043's frontier uses, so the
comparison is against a stated statistical scale rather than an invented cutoff — the rule this
project applied when refusing a capture ratio against a noise-level net oracle (ADR-055).

## Alternatives considered

- **Test the gap for significance per symbol (paired bootstrap over bars).** Rejected for now as a
  much larger unit — it needs the return series of two finalists per symbol re-simulated, which the
  pool does not store. The median-gap-versus-SE statement is the honest summary available from what
  is already recorded, and it is stated as a comparison of scales, not as a p-value.
- **Report the gap without a verdict.** Rejected: a bare "+0.079" invites the reader to supply their
  own scale, which is precisely how "0% power at oracle 1.3" survived for weeks.
- **Rank categories by DSR rather than in-sample Sharpe.** Rejected: within one experiment the
  whole-search haircut is common to every family, so the DSR ordering is the Sharpe ordering — but
  the Sharpe is the quantity Lo's SE applies to, so it is the honest one to compare against a SE.
- **Change the search to break ties differently.** Rejected as an action taken before the
  measurement exists in the repo. Measure first, in the report the project reads every session.

## Consequences

- The pool report gains a line that may read uncomfortably: for a typical symbol the family the
  search selects is within one standard error of the runner-up. That is the point of the report.
- It gives ADR-058's "next unit is the selection step" a target that can be tracked over time: if a
  future change makes family selection separable, this number moves.
- `separable` will read `None` until the next daily-discovery run writes rows carrying `n_bars`
  (ADR-052 amendment), and the printed line says so rather than implying a measured negative.

## Reversal

Drop `CategorySeparation`, the `category_separation` field, its builder block and the report lines.
Nothing else reads it; no stored experiment changes.
