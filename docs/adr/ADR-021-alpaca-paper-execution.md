# ADR-021: Real Alpaca paper-broker execution (reconcile the paper book to Alpaca)

- **Status**: Accepted
- **Date**: 2026-07-08
- **Deciders**: Joe Frasca
- **Builds on**: ADR-019 (forward-testing / paper trading), ADR-020 (managed lifecycle)

## Context
ADR-019 built the forward-sim: a frozen graduate is scored on unseen daily bars, filled at the
close by our own engine. That answers the statistical question (out-of-time Sharpe vs buy-and-hold)
but produces **no broker-side record** — nothing shows in an Alpaca dashboard, and there are no real
(paper) fills. Joe's north star (DELEGATION.md) is to actually **paper-trade the managed book on
Alpaca** so P&L accrues in a real account before any real money is ever discussed.

Alpaca's free tier includes a paper account at `https://paper-api.alpaca.markets/v2` (distinct from
the *data* host `data.alpaca.markets`). The keys are already provisioned in gitignored
`backend/.env` and as GitHub Actions secrets (ADR-019 follow-on).

## Decision
Add a thin **broker adapter** + **sizing/reconcile** layer under a new `app/execution/` tree that
mirrors the OPEN paper positions into real paper orders on Alpaca.

- `AlpacaBroker(base_url, api_key, secret_key, *, fetcher=None)` — a minimal REST client exposing
  `account()`, `positions()`, and `submit_order(symbol, qty, side)`, each returning a frozen
  pydantic model. The network glue is a single injectable `_fetch` method carrying `# pragma:
  no cover` — **the exact pattern from `app/data/sources/alpaca.py` and `edgar.py`** — so mapping and
  order logic are unit-tested at 100% with a fake fetcher; the real round-trip is a `@pytest.mark.live`
  smoke against the paper account.
- **Paper-only guard.** The constructor rejects any `base_url` that is not the Alpaca *paper* host.
  A real-money endpoint can never be reached from this code path (CLAUDE.md rule 7 — paper only).
- `sizing.equal_weight_targets(quotes, equity)` → a signed whole-share `TargetPosition` per name.
  Each OPEN `PaperPosition` is resolved to a `PositionQuote(symbol, signal, price)` by running its
  frozen strategy over recent bars and taking the **latest** position weight (in [-1, 1], honoring
  long/flat/short and fractional conviction). Equity is split equally across names with a non-zero
  signal; each name's dollar target is `slice * signal` (signed), converted to whole shares by
  truncation toward zero. Flat (signal 0) → target 0.
- `reconcile(broker, targets)` diffs Alpaca's current positions against the targets and submits the
  **minimum** orders to close the gap. It is **idempotent**: re-running with the book already at
  target places zero orders. A name whose sign flips through zero (long→short or short→long) is
  split into two orders — close to flat, then open the reverse — because Alpaca rejects a single
  equity order that crosses zero.

## Options Considered
- **Reuse `AlpacaDataAdapter`'s host/client.** Rejected: the paper-broker API is a different host,
  auth is the same headers but the endpoints/response shapes are entirely different (account, orders,
  positions), and conflating data and execution invites pointing execution at the wrong base URL.
- **Fractional-share sizing.** Deferred: whole shares keep the reconcile diff a clean integer and
  therefore trivially idempotent. Fractional dust from external activity is truncated and documented,
  not chased.
- **A full order-management system (limit orders, brackets, TIF variants).** Out of scope — daily
  long-horizon strategies (ADR-015) rebalance at the close; market/day orders suffice. Microstructure
  stays out (ADR-001).
- **Let sizing scale only by signal sign (ignore magnitude).** Rejected: vol-targeted and blended
  strategies emit meaningful fractional weights; honoring magnitude is faithful to the strategy.

## Consequences
- The OPEN paper book (CRM + LOW today) can be mirrored to a real Alpaca paper account; P&L shows in
  the dashboard and accrues on real (paper) fills, complementing the deterministic forward-sim.
- New surface: `app/execution/{alpaca_broker,sizing}.py`. No existing module changes — this WP owns a
  fresh tree. The wiring into a scheduled script (a `paper-broker` step) is a **follow-on**, kept out
  of this ADR so the adapter lands independently and TDD-clean.
- Reconcile is stateless and idempotent, so a cron can run it every day safely; a missed run
  self-heals on the next pass.
- Paper only. Reaching a real-money endpoint is structurally impossible (constructor guard). Real
  capital remains a future, explicitly separate ADR.

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*
