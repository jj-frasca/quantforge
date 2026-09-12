# FINDING-021: Panel-null observed statistic does not match the null search unit

- **Severity:** High — the planned panel inference compares different search/window estimands
- **Found:** 2026-09-12 by Codex hostile review of ADR-081 real-side provenance
- **Status:** Resolved by ADR-085
- **Affected:** `select_panel_null_cohort`, `prepare_panel_null_source_files`,
  `PanelNullCohort.symbol_excesses`

## Finding

ADR-081's null arm runs one production search per symbol on one exact, common 7,400-row prepared
panel. Its observed arm instead copies excess diagnostics from retained pool experiments and takes a
per-symbol median across repeat searches. Those searches can have different row counts, calendar
starts, and completion dates. The two arms therefore do not apply the same statistic to observed
and resampled data.

The equal-symbol outer median fixes run-frequency weighting, but it does not make a median of
several overlapping searches equivalent to the null arm's one search. Nor can `n_bars` prove the
calendar identity of a stored experiment: `Experiment` records only the count and creation time,
not the source endpoints used by `run_search`.

## Evidence

On committed master data at `ace725ae`, using the current search/gate fingerprints and ADR-084's
7,400-bar floor:

- 195 eligible experiments collapse to 39 symbols;
- every symbol contributes five daily searches dated 2026-09-07 through 2026-09-11;
- retained histories span 7,440–8,120 rows, with median 7,785 and 131 distinct row counts; and
- the planned null arm runs one search per symbol on exactly 7,400 aligned rows from one frozen
  source start/end pair.

The measurement remains unspent, so no generated artifact or published panel inference is affected.

## Impact

A completed artifact could report a precisely calculated Monte Carlo tail probability for the
wrong comparison. A difference could reflect history length, calendar regime, or repeat-search
aggregation rather than the contemporaneous dependence ADR-081 is intended to measure. ADR-074
already demonstrated that changing calendar history can materially move raw out-of-sample
diagnostics, so this provenance mismatch is not safely ignorable.

## Required correction

Use the retained pool only to choose the eligible equal-symbol cohort. After the exact prepared
source panel is frozen, run the unmodified production search once on each observed source column
and derive the real paired excesses from those results. Freeze those source-matched values in the
cohort consumed by every null replicate. The observed and null arms must share symbol set, exact
row count, source calendar, search/gate policy, and executed code revision.
