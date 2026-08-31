# ADR-073 — A position that never traded is UNMEASURED, not failed

**Status:** Accepted
**Date:** 2026-08-31
**Supersedes:** none — amends the ADR-020 exit policy

## Context

The managed paper book (ADR-019/020) has returned **−8.74% since inception against a benchmark of
+0.18%**, with roughly half of capital sitting idle in cash. Read as a performance result that says
the research has no edge. It does not say that. It is an artifact of the exit rule.

`ExitPolicy.min_forward_bars_before_exit = 21` is documented as "~1mo grace: don't cut on entry
noise". It counts **bars**, not **trades**. Most strategies in the catalog fire rarely by
construction: `rsi_mean_reversion` and `trend_filtered_mean_reversion` need a threshold crossing
(e.g. `z_threshold = 2.25`) that has roughly a 1–2% daily chance of occurring. Over a 21-bar grace
window the probability such a strategy takes **no position at all** is above one half.

When it takes no position its forward return series is all zeros. `sharpe_ratio` documents that it
returns `0.0` for a constant/degenerate series, so `rolling_sharpe` is `0.0` — not measured, but
**manufactured by the degenerate-series guard**. Both exit rules then fire on it:

- `rolling_sharpe <= min_rolling_sharpe` → `0.0 <= 0.0` → "edge has decayed"
- `require_beat_buy_and_hold_forward and rolling_sharpe <= rolling_bh_sharpe` → true whenever the
  name drifted up → "no longer beats holding the name"

Verified directly against the live policy: a 21-bar all-zero forward series exits **unconditionally**,
whichever way the underlying moved.

The evidence in `data/paper_portfolio.json` matches exactly. Of 27 closed positions, **18 never
took a single trade before being closed**, and the recorded reasons are 24 × "no longer beats
holding the name" and 22 × "edge has decayed" — verdicts on strategies that never expressed an
opinion. 6 of the 17 currently-open positions are in the same state.

The result is a churn treadmill: promote a graduate → it does not fire within 21 bars → its
manufactured `0.0` Sharpe fails both rules → cut → capital returns to cash → repeat. That is the
mechanism behind both the idle cash and the drawdown, and it means the book has never actually
tested whether the research has an edge.

This is the **third** instance of the failure mode ADR-063 and ADR-070 recorded: *stating a
criterion on a statistic that cannot support it.* ADR-063 phrased one over cells with nothing to
find; ADR-070 over per-cell rates whose SE was 3× any plausible effect. Here the statistic has no
sampling distribution at all — on zero trades `sharpe_ratio` is a constant by definition, and the
exit rule reads that constant as a failing grade.

## Decision

**Separate "no evidence" from "bad evidence" in the exit policy.** The Sharpe-based rules are
verdicts on a strategy's trading, and they may only be applied to a position that has traded.

1. `lifecycle_from_returns` takes the number of forward trades explicitly. It is a required
   argument, not an inferred one — a rule this load-bearing should not be able to run on a caller's
   omission.
2. With **zero** forward trades, the Sharpe and drawdown rules are not evaluated at all. Instead:
   - fewer than `max_bars_without_trade` forward bars → **hold**, reason *"not yet measurable"*;
   - at or beyond it → **exit**, reason *"never traded"*.
3. `max_bars_without_trade` defaults to **126 bars (~6 months)**. A position that has not fired in
   six months is not being judged for poor performance; it is being retired because its signal is
   too rare to evaluate on any horizon the book can afford to hold. That is a research finding
   about the parameterization, and it is recorded with distinct wording so it can never be read
   back as "the edge decayed".
4. `ForwardScore` carries `forward_trades`, and `beats_buy_and_hold` is **False** whenever
   `forward_trades == 0`. A strategy that never traded did not beat holding the name. Today the
   comparison returns `True` in that case whenever the name fell — it scores *not participating in
   a decline* as a win, which is how inert positions came to look like the book's best performers
   (DVA: strategy `0.0000` vs buy-and-hold `−21%`, recorded as a win).

`beats_buy_and_hold` stays a `bool` rather than becoming `bool | None`. The tri-state is more
honest in the abstract, but it propagates into the API schema and the frontend Zod guards for a
field that is a display artifact; `forward_trades` carries the same information without the ripple.

## Consequences

- **Positions are held materially longer.** This is the point: the book has never held a strategy
  long enough to find out whether it works. Expect the open count to rise and idle cash to fall.
- **Idle capital is now visible rather than churned away.** A position that is held but not trading
  still ties up an allocation slot. This ADR deliberately does not size positions or reallocate
  unused capital; that is a separate decision and must not be smuggled in as part of a bug fix.
- **`max_bars_without_trade = 126` is an assumption, not a measurement.** It is chosen as a
  plausible upper bound on how long a rare-firing daily strategy deserves before retirement. It
  should be calibrated against the observed distribution of time-to-first-trade once positions
  survive long enough to produce one. **Do not read the current default as evidence-backed.**
- **The historical exit record is now known to be unreliable.** The 18 zero-trade closures in
  `paper_portfolio.json` are not evidence of decayed edges and must not be cited as such. They are
  kept as an honest record, per ADR-019.
- **The −8.74% is not re-litigated by this change.** Fixing the rule does not recover the drawdown
  or retroactively validate the research. It restores the book's ability to measure — nothing more.
  Any claim about edge must wait for positions that have actually traded.
