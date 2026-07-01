# ADR-015: Data frequency, statistical-power policy, and gate calibration for the StrategyLab

- **Status**: Accepted
- **Date**: 2026-07-01
- **Deciders**: Joe Frasca
- **Refines**: ADR-014 (pins the hand-waved holdout + thresholds), ADR-008 (validation-first)

## Context
ADR-014 committed to an agentic search harness gated by the validation stack, but left two
things vague: the **data frequency/length** the search runs on, and whether the graduation
gate uses **fixed** thresholds. Both determine whether the lab is actually *effective* or just
produces statistically hollow "winners." Research (2026-07-01) settles it:

- **yfinance intraday is capped by lookback**, not by request: 1m = last 7 days, 2m–90m = last
  60 days, 1h = ~730 days, **only 1d has multi-decade history**
  ([yfinance docs](https://ranaroussi.github.io/yfinance/reference/yfinance.price_history.html)).
- **Observations ≠ statistical power.** 1-minute bars for 7 days is ~2,700 points inside a
  *single* market regime; validation on that "confirms" a strategy that only knows last week.
  Daily bars over 15 years is ~3,780 points spanning 2008/2020/2022 — fewer points, far more
  regime coverage, and transaction costs are a small fraction of a daily move rather than
  dominating it.
- The Deflated-Sharpe literature we already implement shows there is **no fixed minimum
  sample**: the **Minimum Backtest Length grows with the number of trials** — `minBTL ≈
  2·ln(N)/SR²` ([Bailey & López de Prado](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551)).
  Justifying a Sharpe-1 strategy found after ~100 trials needs ~9 years of daily data. A
  trial-hungry search **cannot clear its own bar on short/intraday history.**
- Product intent (Joe): long-term / position strategies, **not** day trading. Paper trading is
  the eventual proof; Alpaca's **paper trading is free and its free data tier (delayed + IEX)
  suffices for daily** — the $99/mo SIP tier only buys real-time intraday data we don't want.

## Decision

1. **Daily bars are the fixed signal frequency for the lab.** Not a fallback — the deliberate
   design center. Intraday signals are out of scope until a vendor swap *and* a microstructure
   cost/slippage model exist (a future ADR); they are not a config knob.

2. **The lab uses maximum available daily history**, not the UI's 5-year default. A lab data
   request pulls the longest daily span the vendor has for the symbol (target ≥ 15y where it
   exists). Regime coverage is the fuel for honest validation. (The 5y UI default stands for
   interactive use; the lab default is separate.)

3. **New gate: Minimum Track Record Length (MinTRL / minBTL).** A candidate cannot graduate
   unless its track record is long enough for its observed Sharpe *and* the trial count that
   produced it, per Bailey & López de Prado. Implemented as a tested function alongside the
   existing DSR/PBO gates. This is the concrete "is this even enough data?" check ADR-014 lacked.

4. **Bounded, counted trial budget.** Each search has a capped trial budget; the research pool
   aggregates *lifetime* trials per symbol/universe, and that count feeds the DSR penalty and
   the MinTRL gate. Unbounded hunting raises the bar it must clear — by design.

5. **Gate thresholds are versioned, tunable config — never hardcoded constants — and are
   calibrated every search.** Per Joe: "constantly tuning every single search to make the
   system better." Concretely: a `GateConfig` (DSR/PBO/walk-forward/MinTRL/holdout thresholds
   + trial budget) is recorded *with each experiment* in the pool. The calibration loop reviews
   outcomes (did graduates survive the holdout? did rejects that we spot-checked actually fail?)
   and proposes threshold adjustments as new versioned `GateConfig`s. Tuning is data-driven and
   auditable, not vibes; every result is reproducible against the exact config that judged it.

6. **Holdout is fraction-based and split before search.** The most recent ~15–20% of the daily
   span (floor ~1 year) is the locked out-of-sample set, split before any search and structurally
   unreachable by search tools (they receive a handle that cannot resolve the holdout). Read once,
   when a finalist is scored.

7. **Paper trading (later) runs on Alpaca's free tier.** Daily-frozen strategies, paper fills;
   no intraday, no $99 SIP subscription. Chosen when the engine produces holdout-validated winners.

## Options Considered
- **Add intraday/Alpaca now.** Rejected: yfinance can't supply intraday history for validation,
  Alpaca intraday needs a microstructure cost model we don't have, and Joe wants long-term
  strategies. Real cost today: delays the first validated winner for capability we won't use.
- **Fixed 5-year lookback (current UI default).** Rejected: insufficient minBTL once the search
  runs realistic trial counts — it would manufacture false positives the DSR is meant to catch.
- **Fixed gate thresholds.** Rejected: contradicts the "improve every search" intent and can't
  adapt as the pool teaches us which thresholds actually separate signal from luck.
- **This decision:** daily + max history + MinTRL gate + trial budget + versioned, continuously
  calibrated `GateConfig` + fraction-based locked holdout; Alpaca paper (free) later.

## Consequences
Easier:
- The lab is statistically honest by construction — it can't "win" on data too short for its
  own trial count. Every graduate is a reproducible claim tied to the exact `GateConfig`.
- The calibration loop turns each search into training signal for the *system*, not just a
  one-off result — the pool compounds.
- Zero incremental cost: daily (yfinance) + paper (Alpaca free) is a $0 path.

Harder / new obligations:
- Must implement MinTRL from the paper (tested; exact constant verified against the source),
  the `GateConfig` versioning + per-experiment recording, and the calibration review.
- The holdout's structural-unreachability must be enforced in code, not convention (ADR-014).
- Long-history daily fetches are heavier on first ingest (cache-aside amortizes it).
- Intraday and any real-money step remain deferred (ADR-001 still in force until superseded).

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*
