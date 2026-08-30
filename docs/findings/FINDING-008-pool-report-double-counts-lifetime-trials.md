# FINDING-008: Pool reporting double-counts cumulative lifetime trials

- **Severity:** High (methodology reporting; the dashboard misstates the DSR/MinTRL denominator)
- **Status:** Resolved by ADR-066
- **Affected:** `PoolReport.n_trials`, pool-report CLI, dashboard deflation headline

## Finding

Every `Experiment.lifetime_trials` is already cumulative for its symbol: prior lifetime trials plus
the current search's evaluated configurations. `summarize_pool` sums that field across every
retained experiment. Repeated hunts therefore count the same prior trials once in every later row.

For one symbol with cumulative experiments 10, 20, and 30, the DSR and MinTRL denominator on the
latest search is 30, but the report publishes 60. Pool retention makes the multiplier bounded but
does not make the sum meaningful. ADR-062 now correctly carries the counter forward in production,
so the reporting inflation will grow faster after every daily hunt.

## Evidence

- `_trials_for_symbol` defines the operative denominator as the **maximum** cumulative
  `lifetime_trials` for a symbol so it survives pruning.
- `summarize_pool` instead computes `sum(e.lifetime_trials for e in experiments)`.
- The existing unit fixture gives repeated rows for the same symbol identical, non-cumulative
  values, masking the defect.
- The frontend labels this sum “lifetime trials” and says it is the denominator used by Deflated
  Sharpe and MinTRL.
- On the committed 2026-08-29 pool, the old row sum is **614,367** while the sum of the actual
  per-symbol maxima is **122,157**: a 5.03x overstatement of the represented denominator.

## Impact

The gate itself remains correctly priced after ADR-062, but the public headline overstates how many
hypotheses the gate has priced. The error can make the research programme look more exhaustive and
the statistical penalty look larger than either actually is. Because the number is presented as
methodology evidence, this is not a cosmetic counter bug.

## Required behavior

Report the sum, across distinct symbols, of each symbol's maximum cumulative `lifetime_trials`.
Describe it as the sum of the per-symbol DSR/MinTRL denominators rather than one global denominator.
Preserve all stored experiments and generated data unchanged.
