# FINDING-072: Paper-book alpha conflates pre-tracking drift with the benchmark window

- **Severity:** Medium — the headline "are we making money vs. the market?" number is measured
  over two different windows and materially overstates the book's underperformance; not yet
  surfaced in the frontend, but persisted as durable record and printed in every broker-run log
- **Status:** Resolved — fixed by ADR-141 (`be33355d`), surfaced on the dashboard by `7e133d29`.
  `append_equity_point` now derives alpha from `history[0].equity` (the benchmark's own inception
  point), not from `return_since_start`'s nominal $100k baseline. Live-verified against the running
  frontend and `data/equity_curve.json` (2026-09-27).
- **Date:** 2026-09-27
- **Affects:** `app.execution.equity_curve.append_equity_point`, `scripts/paper_broker.py::main`,
  every `alpha_since_start` value in `data/equity_curve.json` computed since benchmark tracking
  began (2026-08-19 onward)

## Finding

`equity_curve.py`'s own docstring calls `alpha_since_start` "the ONLY honest 'are we making
money?' question" — the book's return minus the benchmark's return "over the same window." It is
not measured over the same window.

`return_since_start` is always computed against a fixed nominal constant,
`_PAPER_STARTING_EQUITY = 100_000.0`. `benchmark_return` (`paper_broker.py::main`, lines ~90-97) is
computed as SPY's return from `inception = history[0].timestamp` — the timestamp of the very first
equity-curve snapshot ever recorded — to now. `alpha_since_start = return_since_start -
benchmark_return` then silently subtracts a benchmark return measured from **the first recorded
snapshot's date** from a book return measured from **a nominal $100k that was never actually
observed on that date**.

Verified directly against the committed data (`data/equity_curve.json`, not assumed): the very
first snapshot (`2026-08-05T02:07:04Z`) already shows `equity: 92488.99`, `n_positions: 3` — real
trading had already happened before this tracking series starts, and the account was already 7.5%
below the nominal $100k baseline the very first time it was ever recorded. That 7.5% gap opened
**before** the benchmark's clock starts (benchmark tracking only exists from 2026-08-19 onward,
per `git log` on `equity_curve.py`), so it is never subtracted out of `return_since_start`, yet it
is permanently baked into every `alpha_since_start` computed since, because `return_since_start`
never resets to the account's actual state at the benchmark's own inception point.

Concretely, at the latest snapshot (`2026-09-26T06:36:04Z`): `equity=86050.87`,
`return_since_start=-0.1395`, `benchmark_return_since_start=+0.0045` (SPY since 2026-08-05),
reported `alpha_since_start=-0.1440`. The book's actual return **over the same window the
benchmark measures** (2026-08-05 equity 92488.99 → now) is `86050.87/92488.99 - 1 = -0.0696`, so
the honestly-windowed alpha is `-0.0696 - 0.0045 = -0.0741` — roughly **half** the currently
reported figure. The metric this project brands as the one honest performance question currently
overstates the book's underperformance vs. SPY by about 7 points, purely as an artifact of mixing
a fixed nominal baseline with a benchmark window that starts later than that baseline's own
(unobserved) starting moment.

This is not yet rendered in the frontend (`EquityCurvePanel.tsx` only displays
`return_since_start`, correctly labeled "since $100k start" — that specific number is honest and
unaffected by this finding). But `alpha_since_start` is persisted to the committed
`data/equity_curve.json` time series and printed in every scheduled `paper-broker.yml` run's log
(`f", alpha {latest.alpha_since_start:+.2%} vs SPY"`), so it is already a durable, quoted number,
not dead code.

Root cause is structural, not a typo: `append_equity_point` has access to `history` (and therefore
`history[0].equity`, the book's actual equity at the benchmark's own inception point) but never
uses it — it derives `alpha` purely from `return_since_start`, which is anchored to a *different*
reference point than `benchmark_return`.

## Required correction

Compute the book's own return over the **same window** the benchmark uses — from
`history[0].equity` (or the current point's own equity, when it is the first point) to the current
equity — and subtract the benchmark return from *that*, not from `return_since_start`. Leave
`return_since_start` itself untouched: "return vs. the nominal $100k paper start" is a distinct,
honestly-labeled question and stays correct as-is. Do not backfill or rewrite historical
`alpha_since_start` values already committed to `data/equity_curve.json` (ADR/charter: never
rewrite committed data-file history) — they remain an honest record of what was reported at the
time, under the old formula; only new appends should use the corrected one.
