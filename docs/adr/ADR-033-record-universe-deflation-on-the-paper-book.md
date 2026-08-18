# ADR-033: The paper book records the universe-deflation verdict — and reports the two cohorts apart

- **Status**: Accepted
- **Date**: 2026-08-18
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Extends**: ADR-018 (universe deflation), ADR-019 (forward testing), ADR-020 (managed paper book)

## Context
ADR-018 added the honest cross-symbol-selection bar. Selecting the best of N symbols under the null
produces an expected maximum annualized holdout Sharpe of roughly `√(1/T_years) · √(2 ln N)`, and
`rank_experiments` already computes, per graduate, whether its holdout Sharpe clears it —
`LeaderboardRow.survives_universe_deflation`. ADR-018's own words: *a graduate must clear this to be
distinguishable from lucky selection.*

**The managed paper book ignores it.** `manage_portfolio` promotes every graduate it finds, and
`freeze_graduate` does not carry the verdict onto the position. Measured against the live pool on
2026-08-18:

```
symbols in pool                     607
graduate experiments                206
leaderboard graduates (best/symbol)  40
                       ... that survive universe deflation:  0
```

Not one. The closest is `CASY rsi_mean_reversion` at a 1.64 holdout Sharpe against a 1.73 bar; the
next tier — seven `VRT triple_ma_alignment` configs at 1.29–1.43 — faces a 2.84 bar because its
holdout is only 1.6 years. Meanwhile the paper book holds 21 open positions drawn from exactly that
population, and the Alpaca paper account stands at −5.4% since inception.

So the project computes a rigorous multiple-testing bar, publishes it on the leaderboard, and then
allocates (paper) capital as if it did not exist. That gap is the single most misleading thing in
the system: it is a rigor claim the pipeline does not honour.

## Decision
**Record the universe-deflation verdict on every position at freeze time, and report the book as two
cohorts — survivors and non-survivors — wherever forward performance is summarized.**

`PaperPosition` gains three recorded-at-promotion fields:

- `survives_universe_deflation: bool | None`
- `universe_deflation_bar: float | None` — the threshold it was measured against
- `universe_n_symbols: int | None` — the N that produced that threshold

They are recorded, not recomputed, because the bar depends on the universe size *at the moment of
selection*. A position promoted when the pool held 60 names was not subjected to the same test as
one promoted at 607, and back-computing today's N would silently rewrite history.

`manage_portfolio` takes the universe size and threshold source it selected from, and
`deflation_cohorts()` summarizes forward performance split by the verdict.

### Why not block promotion on it
The obvious alternative — refuse to promote anything that fails the bar — would empty the book and
keep it empty, and it would destroy the only data that can ever answer the question that matters:
**does the deflation bar actually predict forward performance?** The non-survivors are the control
group. A forward test whose population is pre-filtered by the very statistic under evaluation cannot
measure that statistic.

This is emphatically **not** weakening a threshold (charter §4). The graduation gate is untouched,
the bar is untouched, and nothing that failed is relabelled as passing. What changes is that the
verdict becomes visible on every position and in every summary, instead of being computed and
discarded. A book reported as *"21 open, 0 of which clear the universe-deflation bar"* is a far more
honest artifact than one reported as *"21 graduates"*.

### Re-evaluation trigger
When at least 20 positions in each cohort have accrued ≥126 forward bars (~6 months), compare the
cohorts' forward Sharpe. If survivors materially outperform, promote the bar to a hard promotion
gate in a follow-up ADR. If they do not, that is a publishable negative result about ADR-018's
calibration — and it should be written up, not buried.

## Alternatives considered

- **Hard-gate promotion on the verdict.** Rejected above: empties the book, and destroys the control
  group needed to validate the bar itself. Revisit at the trigger.
- **Recompute the verdict at report time from today's N.** Rejected: it rewrites the test each
  position was actually subjected to, and makes a position's status drift with universe growth for
  reasons unrelated to its own performance.
- **Lower N to "effectively independent" symbols** (e.g. cluster correlated names). Defensible and
  genuinely interesting — 607 US equities are nowhere near 607 independent bets, so `√(2 ln N)` is
  conservative. But it is a research question with its own methodology, not a wiring change, and
  guessing at an effective N to make the bar easier to clear is precisely the move charter §4
  forbids. Worth its own ADR with evidence.
- **Say nothing and keep promoting.** Rejected: that is the status quo, and it is the dishonest one.

## Consequences

- Every summary of the paper book now leads with how many positions clear the bar. Today that number
  is zero, and the system says so.
- Positions frozen before this ADR carry `None` for all three fields — honestly unknown, not
  retroactively assumed. They are excluded from cohort comparisons rather than assigned a cohort.
- The promotion path needs the universe size threaded through `manage_portfolio`, so callers that
  promote (the discovery consolidation and the weekly hunt) must pass what they selected from.

## Reversal
Drop the three fields from `PaperPosition` and the `universe_n_symbols` argument from
`manage_portfolio`. They are additive and defaulted, so persisted books keep validating either way,
and no promotion, exit, or sizing decision depends on them.
