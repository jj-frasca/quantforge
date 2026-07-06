# ADR-019: Forward-testing / paper trading (supersedes ADR-001's no-paper-trading scope)

- **Status**: Accepted
- **Date**: 2026-07-02
- **Deciders**: Joe Frasca
- **Supersedes**: ADR-001 (the "no paper trading, no order books" scope limit only)

## Context
ADR-001 scoped QuantForge as a research/validation platform — explicitly **no paper trading**.
That scope is now intentionally changed (Joe, 2026-07-02): the validation platform is built and
proven, and the next step is to put its findings to the one test no statistical correction can
substitute for — **out-of-time performance on genuinely unseen data.**

This is forced by ADR-018: the two in-sample graduates (CRM, LOW) do **not** survive universe-level
deflation, i.e. from history alone they're indistinguishable from lucky cross-symbol selection.
The honest — and only — way to certify them is to **freeze them now and watch them forward.**

## Decision
Add a **forward-testing / paper-trading** subsystem. A frozen graduate becomes a *paper position*:
its (symbol, strategy, params) is locked with an as-of date; from then on, each new daily bar is fed
to the strategy, positions update, and a live paper equity curve accrues on **data the strategy has
never seen and could not have been fit to.**

Substrate — two stages:
1. **Daily forward-sim on yfinance (now, $0, no account).** Each day: fetch new EOD bars, apply the
   frozen signal, mark the paper portfolio to the close. Matches ADR-015's daily mandate and Joe's
   long-term (not day-trading) intent. Fills modelled at the close with the engine's existing cost
   model. This is a *simulation*, honestly labelled — not broker fills.
2. **Alpaca real-broker paper (follow-on).** Real paper account + real(ish) fills via Alpaca's free
   tier (paper trading is free; delayed/IEX data suffices for daily). Needs Joe's Alpaca API key.
   A thin broker adapter behind the same portfolio interface; the forward-sim is the fallback.

Core pieces (each ADR-lean, TDD):
- `PaperPosition` — a frozen graduate + as-of date + accrued forward bars/equity, JSON-persisted
  alongside the research pool (in-repo, reviewable).
- `forward_step(portfolio, new_bars)` — deterministic: apply signals, update positions + equity,
  append to the forward curve. Pure over injected bars (testable without network).
- A `paper` CLI / scheduled step that fetches new bars and advances every open paper position.
- **The honest scoreboard:** forward Sharpe/return vs the in-sample + holdout expectation, and vs
  buy-and-hold — the same "did you actually beat holding it?" bar (ADR-016), now truly out-of-time.

Guardrails: paper only — **no real-money orders in this ADR.** Real capital is a future, explicitly
separate decision. Forward results are labelled by substrate (sim vs broker) and never conflated
with the backtest.

## Options Considered
- **Keep ADR-001 (no paper trading).** Rejected: Joe changed the scope; and it leaves the honest
  certification question (out-of-time performance) permanently unanswered.
- **Alpaca real-broker paper first.** Deferred: needs an account/key and adds a broker adapter
  before we've proven the forward loop; the yfinance sim gets us forward-testing today at $0.
- **Jump straight to real money.** Rejected: paper first, always; real capital is its own decision
  with its own risk controls.

## Consequences
- CRM + LOW (and future graduates) get frozen and tracked forward — the real answer to selection bias.
- Forward results accrue in **real time** (a position needs weeks/months of new bars to say much);
  the subsystem is a durable, scheduled process, not a one-shot.
- New obligations: a persisted paper portfolio (in-repo), a scheduled forward step, and honest
  substrate labelling. Real-money trading remains out until a future ADR.
- ADR-001's other limits (no HFT/order-book microstructure) still stand; only the paper-trading
  prohibition is lifted.

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*
