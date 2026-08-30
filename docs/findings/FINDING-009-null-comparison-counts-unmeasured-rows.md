# FINDING-009: Null comparison counts unmeasured rows toward its minimum sample

- **Severity:** High (methodology reporting; an underpowered or wrong-population median can be
  labeled comparable)
- **Status:** Resolved by ADR-067
- **Affected:** `compare_with_null`, `NullComparison.comparable`, pool-report CLI

## Finding

ADR-064 requires at least 30 history-matched experiments before comparing a real finalist median
with a measured null. The implementation applies that minimum to every history-matched experiment,
including rows whose finalist does not carry the statistic being summarized. The median's actual
sample is `NullComparison.real_n`, which can therefore be smaller than 30 while `comparable=True`.

If none of the matched finalists carries the statistic, `_summarize` returns `None` and the code
falls back to the pool-wide diagnostic summary. With 30 or more history matches, that fallback can
be declared comparable even though its observations came from histories outside the matched
population.

## Evidence

- `_matched` selects experiments by `n_bars`, regardless of whether their finalist carries the
  diagnostic.
- `_mismatch` checks `len(matched) < MIN_MATCHED` but receives no count for the statistic's
  non-null observations.
- `compare_with_null` reports `real_n` from `_summarize`, proving the measurement already knows its
  smaller effective sample.
- A focused regression with 40 history matches and only five measured finalists fails before the
  correction: both five-observation medians are marked comparable.

## Impact

The report can present a noisy median as a formally valid real-vs-null comparison and can, in the
all-missing case, compare the null with a median computed from the wrong history cohort. This
undermines the load-bearing `comparable` field even though the history and search fingerprints
themselves match.

## Required behavior

Keep ADR-064's minimum of 30 and apply it to the number of non-null finalist diagnostics in the
matched subset. Preserve `matched_n` as the transparent history-cohort size and `real_n` as the
displayed diagnostic sample. A fallback median may remain visible on a refused row, but it must
never become comparable when fewer than 30 matched diagnostics produced it.
