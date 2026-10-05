# FINDING-106: Monte Carlo risk silently discards return evidence

- **Date:** 2026-10-05
- **Severity:** High — undefined observations can yield apparently measured risk
- **Status:** Resolved by ADR-174

## Evidence

`analyze_strategy_risk` calls `returns.dropna()` before estimating daily moments. A supplied
series `[0.01, NaN, 0.01]` therefore becomes two constant positive observations and publishes
zero terminal-loss and drawdown probabilities, identical to a different, complete two-row series.
The missing return has no known value, so this result does not measure the supplied history.
The same public boundary accepts finite returns at or below -1, incompatible with its positive
GBM wealth model; e.g. `[-1, -1]` still produces positive simulated wealth. Boolean returns also
become numerical observations despite having no return-value meaning.

## Correction and limits

ADR-174 rejects incomplete, non-real/non-numeric, nonfinite, and wealth-destroying return evidence
before estimation. It preserves all complete real numeric series greater than -1, the two-row
minimum, ordinary moment formulas, seeded simulations, and loss comparisons. This is an offline
boundary reproduction, not evidence that a stored report or a production engine supplied bad
returns. Calendar identity, iid/GBM assumptions, and numerical stability of summary estimates are
separate questions. No generated data or validation threshold changes.
