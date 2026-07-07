# ADR-020: Managed paper portfolio — full lifecycle with automatic exits

- **Status**: Accepted
- **Date**: 2026-07-07
- **Deciders**: Joe Frasca
- **Extends**: ADR-019 (forward-testing/paper trading)

## Context
ADR-019 freezes graduates as paper positions and scores them forward, but only ever ENTERS —
it never exits. For a system heading toward real money that is dangerous: a strategy's edge can
decay day over day (regime change, crowding, the edge was luck), and a book that only adds and
never cuts is how real capital gets destroyed. Joe (2026-07-07): "not only do we need graduates
but if they start sucking we need to get rid of them... think about if this were real money."

So the portfolio must be a **managed book** with a full lifecycle: promote winners in, monitor
them daily on a *rolling* window, and **exit automatically** when they deteriorate.

## Decision
A `PaperPosition` gains a lifecycle status (`open` / `closed`) with a close date + exit reason.
A tunable, versioned **`ExitPolicy`** (same calibration philosophy as GateConfig, ADR-015) drives
a daily `evaluate_lifecycle(position, frame, policy) -> LifecycleDecision` (`hold` / `exit` + reasons).

Exit is evaluated on the **forward** slice only (post-freeze — the honest out-of-sample record),
using a *rolling* trailing window so a strategy that was good early but is bad lately gets cut:
- **Grace period:** no exit until `min_forward_bars_before_exit` (~1 month) have accrued — don't
  cut on noise right after entry.
- **Rolling Sharpe floor:** exit if the trailing `rolling_window_bars` (~3 months) forward Sharpe
  falls at/below `min_rolling_sharpe` (default 0).
- **Forward drawdown limit:** exit if the position's forward drawdown from its peak exceeds
  `max_forward_drawdown` (default 25%).
- **Stops beating buy-and-hold:** exit if, over the rolling window, the strategy's forward Sharpe
  trails simply holding the name (the ADR-016 bar, now applied continuously forward).
Any trigger closes the position with its reason(s) and final forward record.

The daily scheduled job (local cron / cloud workflow) becomes the portfolio manager: for each
OPEN position, evaluate lifecycle and close on `exit`; promote any new hunt graduate not already
held. Closed positions are retained (the honest track record: what worked, what didn't, and for
how long) — never silently deleted.

## Options Considered
- **Entry-only (ADR-019 as-is).** Rejected: unmanaged risk; unacceptable for real money.
- **Cumulative-since-freeze exit metric.** Rejected: a big early gain masks recent rot; rolling
  windows catch decay, which is the whole point.
- **Hard-coded exit thresholds.** Rejected: same reasoning as ADR-015 — `ExitPolicy` is versioned
  + tunable + recorded, so the calibration loop can learn what exit rules actually preserve capital.
- **Delete losers.** Rejected: the record of a failed strategy (and why/when it failed) is
  valuable evidence; close and keep it.

## Consequences
- The portfolio is a living managed book: winners in, losers cut, every day, autonomously.
- Honest, auditable track record of entries AND exits — exactly what proves (or disproves)
  skill before real money.
- New obligations: `ExitPolicy` versioning, rolling forward metrics, and the daily job gains
  promote + monitor + exit steps.
- Position sizing / capital allocation across the book, and REAL order execution, are the next
  ADRs (Alpaca paper orders); this ADR governs the entry/monitor/exit *decisions*.

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*
