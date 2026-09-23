# FINDING-038: PBO silently scores non-finite return matrices

- **Severity:** High
- **Status:** Resolved by ADR-106
- **Found:** 2026-09-22, Codex autonomous session 6
- **Affects:** CSCV PBO and the production graduation gate

## Finding

`probability_of_backtest_overfitting` accepts `NaN` and infinite per-bar returns. A contaminated
subset produces a non-finite mean or standard deviation; the guarded Sharpe division then leaves
that candidate at the output buffer's default `0.0`. PBO continues with a fabricated finite rank
instead of rejecting the invalid evidence.

On a deterministic 300-row, eight-candidate matrix with one persistent winner, valid PBO is
`0.000`. Replacing one return in that winner with `NaN` changes PBO to `0.829`. The caller receives
a valid-looking number in `[0, 1]`, and the strict production gate changes verdict, with no signal
that the statistic was computed from an invalid matrix. Infinity follows the same path and emits
only a runtime warning.

PBO is the first validation consumer of the shared performance matrix, so its boundary is the
right fail-closed point. Missing or infinite returns are not zero-return observations and cannot be
ranked as such. A live validation gate must refuse them rather than manufacture evidence.

## Required correction

Require a two-dimensional, entirely finite performance matrix before computing any CSCV moments.
Also reject geometries that leave fewer than two observations in an IS or OOS half, because sample
standard deviation and Sharpe are then undefined. Add regressions for `NaN`, positive and negative
infinity, malformed dimensionality, and a one-observation half. Do not impute, drop rows, move
`pbo_max`, dispatch calibration, or edit generated data.
