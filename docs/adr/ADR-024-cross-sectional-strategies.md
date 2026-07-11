# ADR-024: Cross-sectional strategy dimension

- **Status**: Accepted
- **Date**: 2026-07-11
- **Deciders**: Joe Frasca
- **Extends**: ADR-014 (research harness), ADR-016 (gate + holdout contract), ADR-022 (value engine)

## Context
Every strategy the lab has searched so far is **single-name**: each symbol is judged in isolation
(`run_search` splits one symbol's frame, backtests configs on that one series, gates the finalist).
That misses a whole class of edges that only exist *across* the universe — where the signal is a
symbol's rank **relative to its peers on the same day**, not its own trailing behaviour. Classic
cross-sectional factors (Jegadeesh & Titman momentum, short-term reversal, value) are constructed
by ranking the whole universe each period and going long the top / short the bottom. They produce
**one portfolio return series per strategy**, not a per-symbol verdict.

We already have a battle-tested graduation gate (ADR-016: DSR > 0, PBO < 0.5, parameter stability,
MinTRL, locked-holdout Sharpe > 0, beat buy-and-hold). The honest thing is to run a cross-sectional
strategy's **portfolio return series** through that *same* gate — a cross-sectional factor should
have to clear exactly the rigor bar a single-name strategy does, no easier.

## Decision
Add a new, self-contained tree `backend/app/research/cross_sectional/` that computes cross-sectional
portfolio return series and reuses the existing gate. It does **not** touch the single-name catalog
(`strategies/`, `catalog.py`), the scripts, or `universe.py`.

### The no-lookahead rule (rank on t, trade t+1)
This is the load-bearing methodology invariant and is enforced as a Hypothesis property test.

- A strategy emits a **signal panel** `S` (dates × symbols) where `S.loc[t, sym]` uses only prices
  up to and including `t` — the same contract as `BaseStrategy.generate_signals`.
- `long_short_weights` turns each row (one date) into **dollar-neutral** target weights: the top
  `quantile` fraction of that day's ranked symbols share `+1`, the bottom fraction share `-1`.
- The engine realizes a portfolio return with `weights.shift(1) * asset_returns` — i.e. the weights
  formed from information at `t` are held to earn the return from `t` to `t+1`. **Rank on `t`, trade
  `t+1`.** This is the identical shift the single-name `BacktestEngine` uses (`position.shift(1)`),
  so `portfolio_return[t]` depends only on prices ≤ `t`. The property test asserts truncation-
  invariance: recomputing on a panel truncated after date `m` reproduces the first `m` returns
  exactly (future prices cannot change a past portfolio return).

### Strategies shipped
- **Cross-sectional momentum** — signal = trailing return over `lookback`, ending `skip` bars ago
  (skip avoids the 1-month reversal). Long past winners, short past losers. Jegadeesh & Titman (1993).
- **Short-term reversal** — signal = *negated* trailing return over a short `lookback` (~5 bars).
  Long recent losers, short recent winners. Lehmann (1990); Jegadeesh (1990).
- **Cross-sectional value** — signal = each symbol's `UndervaluationScore` from the merged value
  engine (ADR-022). Long the cheapest, short the richest. Fama & French (1992); Asness et al. (2013).

### How it reuses the existing gate
`run_cross_sectional_search` mirrors `run_search` at the **portfolio** level instead of the
single-config level:
1. Split the price **panel by date** into an in-sample head and a sealed holdout tail
   (`split_panel_holdout`, same fractions/floors as `split_holdout`).
2. For each strategy, build a config grid, run the engine on the in-sample panel → one portfolio
   return series per config. Stack them into the `(T, N)` matrix and reuse the *existing*
   `probability_of_backtest_overfitting`, `deflated_sharpe`, `parameter_stability`,
   `walk_forward_splits`, `purged_kfold_splits` → an ordinary `ValidationReport`.
3. Score the finalist on the holdout: run it over the **full panel** for warmup, then score only the
   post-split slice (leak-free — weights at date `t` use only prices ≤ `t`, and only holdout dates
   are scored; this mirrors `paper.evaluate_forward` rather than wasting momentum warmup at the
   holdout boundary). The buy-and-hold benchmark is the **equal-weight long-only universe** — the
   cross-sectional analog of "why not just hold it?".
4. Feed the `ValidationReport` + `HoldoutScore` + in-sample track-record years + lifetime trial
   count into the unmodified `GraduationGate.evaluate`. A cross-sectional factor graduates exactly
   the way a single-name strategy does.

### In scope
- Three cross-sectional strategies, a per-period long/short ranker, an engine that produces the
  portfolio return series with transaction costs on turnover, a strategy registry, and a
  search/gate wrapper producing a `CrossSectionalExperiment`.
- Reuse of `Trial`, `Graduate`, `GateConfig`, `GateResult`, and every validation primitive.

### Out of scope (deferred)
- **Time-varying value**: cross-sectional value ranks on a *static as-of* snapshot of each symbol's
  `UndervaluationScore` (ADR-022 gives latest-10-K-only). Point-in-time value *history* is a later ADR.
- Wiring cross-sectional strategies into the CLI hunt / universe sweep, the experiment store schema,
  the paper-trading lifecycle, and the frontend. This ADR lands the engine + gate reuse only.
- Sector/beta neutralization, factor-risk models, and portfolio optimization beyond equal-weight
  dollar-neutral legs.
- Universe-level deflation across strategies (ADR-018 is per-symbol/leaderboard; a cross-strategy
  version can follow).

## Options Considered
- **Reuse `run_search` / `BaseStrategy` directly.** Rejected: those are single-series by contract
  (`generate_signals(data) -> Series` for one symbol); a cross-sectional signal is inherently a
  panel and a portfolio. Forcing it through the single-name path would distort both.
- **Invent a parallel gate for portfolios.** Rejected: the whole point is that a factor must clear
  the *same* rigor bar. We reuse `GraduationGate` unchanged; only the *inputs* are assembled
  differently (portfolio returns instead of one config's returns).
- **Score the holdout on the holdout slice only (no full-panel warmup).** Rejected: momentum needs a
  `lookback`-bar warmup; scoring holdout-only would blank the first ~65 bars of an already-short
  holdout. The full-panel-run / score-the-slice approach is leak-free and matches `evaluate_forward`.

## Consequences
- A genuinely new alpha dimension (option C in the running roadmap) lands without weakening any
  existing rigor — the gate, holdout unreachability, and DSR/PBO/MinTRL penalties all apply.
- New obligation for whoever integrates: wire `run_cross_sectional_search` into a hunt driver and a
  persistent store (the single-name `Experiment` is per-symbol; `CrossSectionalExperiment` is
  per-strategy/universe), then forward-test survivors like single-name graduates.

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*
