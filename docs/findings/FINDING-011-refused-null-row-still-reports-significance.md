# FINDING-011: A refused null comparison still reports a significance interval

- **Severity:** High — methodology reporting can attach `EXCLUDES ZERO` to an invalid comparison
- **Status:** Resolved by enforcing ADR-064/067 before interval computation and rendering
- **Found:** 2026-08-30 by Codex hostile review of ADR-075
- **Affected:** `compare_with_null`, pool-report CLI, `NullComparisonPanel`

## Finding

ADR-064/067 makes `NullComparison.comparable` the load-bearing guard for search-family identity,
matched history, and a minimum of 30 measured diagnostics. ADR-075 computes its clustered
difference-of-medians interval before that guard is evaluated and attaches the interval even when
`comparable=False`. Both the CLI and dashboard then render the interval independently of
`comparable`, including the significance-like label `EXCLUDES ZERO`.

The result can therefore put a formally refused row and a positive separation claim next to each
other. Three measured diagnostics, a mismatched search fingerprint, or no history-matched cohort
can all produce an interval that looks publishable even though the existing methodology says the
underlying populations must not be compared.

The inherited minimum also counts experiments while ADR-075 resamples symbols. Thirty repeat
searches of one symbol satisfy the row-level floor but provide one effective bootstrap sampling
unit, from which the first implementation still published a zero-excluding interval.

## Evidence

- `_excess_rows` calls `_clustered_difference_ci` before `_mismatch`.
- `difference_ci_low`, `difference_ci_high`, and `difference_n_clusters` are populated regardless
  of the resulting `comparable` value.
- The CLI and `NullComparisonPanel` render any non-null interval without checking `comparable`.
- A three-experiment focused fixture is refused by ADR-067's 30-diagnostic minimum but still
  produces and renders an `EXCLUDES ZERO` interval before the correction.
- A 30-experiment fixture collapsed onto one symbol is row-comparable but still produces an
  interval from one cluster before the correction.

## Impact

This does not change a graduation decision or a stored calibration artifact. It does undermine the
reporting boundary that prevents incompatible or underpowered measurements from becoming findings,
and can overstate the newest central methodology claim on future pool states.

## Required correction

A refused row may retain its medians and mismatch as context, per ADR-064, but it must not expose or
render ADR-075's difference interval or its zero-exclusion reading. Apply the existing minimum of
30 to the interval's effective symbol-cluster units as well as to the row's diagnostics. Keep a
frontend guard as defense in depth so a stale or third-party payload cannot reintroduce the
contradiction.
