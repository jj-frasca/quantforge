# FINDING-108: Backtest calendar order can use future signals

- **Date:** 2026-10-05
- **Severity:** High — positional lag can move a future signal into an earlier return
- **Status:** Resolved by ADR-176

## Evidence

`BacktestEngine.run` does not validate its price index before `pct_change` and `position.shift(1)`.
With calendar `[Jan 1, Jan 3, Jan 2]`, prices `[100, 121, 110]` and signals `[0, 1, 0]`, the
Jan 3 signal earns Jan 2's reported -9.09% return. The one-row lag is not causal unless the price
calendar is strictly increasing. Duplicate timestamps similarly create multiple observations at
one instant. The checked ResearchDataset production acquisition boundary requires ordered unique
rows, but the public engine accepts Series directly and `run_strategy` accepts frames; intrinsic
calendar identity must not depend on an earlier caller's check.

## Correction and limits

ADR-176 rejects duplicate or nonascending price calendars before signal alignment and arithmetic.
It does not sort or deduplicate observations, alter lag/cost math, or require a timezone/calendar
kind. Ordered generic indexes, empty/single-row series and sparse signals retain their existing
behavior. This is an offline direct-boundary reproduction, not proof that a production pool row
was scored with a malformed calendar. No generated data or threshold changes.
