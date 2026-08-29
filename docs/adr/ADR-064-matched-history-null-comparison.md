# ADR-064: Compare the pool against the null on a matched-history subset, not on the median

- **Status**: Accepted
- **Date**: 2026-08-29
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-051 (finalist OOS diagnostics vs a measured null), ADR-063 (the 1990 search window)
- **Relates to**: ADR-044 (search fingerprint as a comparability guard), ADR-052 (record the search family)

## Context

ADR-051 established that the pool's out-of-sample Sharpes mean nothing against zero and must be read
against a null measured with the same search, the same gate and the same history length.
`pool_report._mismatch` enforces the last of those as **exact equality of two integers**:

```python
null_bars = int(np.median(calibration.n_bars)) if calibration.n_bars else None
if null_bars is not None and report.median_n_bars not in (None, null_bars):
    reasons.append(f"history {report.median_n_bars} bars vs {null_bars}")
```

**That test can essentially never pass.** The pool's median history grows by one bar per trading day
as symbols are re-searched; the null artifact's is a fixed integer written when the calibration ran.
Today the report refuses all four comparisons partly for `history 5444 bars vs 5400` — a 0.8%
difference — while **2,427 of the 3,028 experiments that state an `n_bars` are within 10% of the
null's 5,400**. The refusal is not protecting a comparison from a distortion; it is discarding a
large, genuinely matched sample because a summary statistic moved by 44 bars.

**ADR-063 turns this from wasteful into misleading.** The search window is now 1990-01-01, so the
pool becomes bimodal: legacy rows at ~5,448 bars and re-searched rows at 7,400+. Measured now, the
distribution is `[0,1k): 25 | [1k,3k): 216 | [3k,5k): 409 | [5k,5.5k): 2,378 | [5.5k,∞): 0`. As the
new cohort fills in, the median walks from 5,444 through values that describe **neither** cohort. A
rule that keys on the median would then compare a null at 7,400 bars against a pool "median" of
6,400 that no experiment resembles — and could report `comparable` at the moment the median happens
to cross the null's integer, which is precisely when the pool is most heterogeneous.

The search-family half of `_mismatch` does not have this problem: a fingerprint is an identity, and
two different fingerprints are two different searches. Only the history half is a *quantity*, and
quantities deserve a tolerance and a subset, not an equality test.

## Decision

**Compare the null against the experiments whose history actually matches it, and say how many
there were.**

1. `compare_with_null(report, calibrations, experiments)` takes the same experiment sequence
   `summarize_pool` was given. For each null artifact it selects the finalists of experiments whose
   `n_bars` is within **`HISTORY_TOLERANCE = 0.10`** of that artifact's median `n_bars`, and
   summarizes the real side over exactly those.
2. `NullComparison` gains `matched_n` (how many experiments the real side was computed from) and
   `matched_n_bars` (the median history of the matched subset). Both are printed. A comparison whose
   sample the reader cannot see is not a measurement.
3. **The comparison is refused when the matched subset is smaller than `MIN_MATCHED = 30`**, with
   the reason stated as such. A tolerance that admits an under-powered sample would trade one
   dishonesty for another.
4. Experiments with no `n_bars` (the 227 legacy rows that predate ADR-052) are **excluded from the
   matched subset**, not assumed to match. They keep triggering the search-family half of the
   mismatch, which is the correct treatment for a row that cannot state what produced it.
5. The search-family check is unchanged and still refuses outright.

## Alternatives considered

- **Keep exact equality and re-run the null whenever the median moves.** Rejected: the median moves
  every trading day, so this is a standing obligation to re-run a multi-hour calibration to chase a
  number that does not change any answer. It is also what the project has been doing implicitly, and
  the result is that the comparison has been refused for months.
- **Drop the history check entirely and compare everything.** Rejected outright: history length is
  the single largest driver of Sharpe dispersion under the null (ADR-051 raised the null from 3,000
  to 5,400 bars for exactly this reason), so comparing a 603-bar experiment against a 5,400-bar null
  compares two different distributions.
- **Widen the tolerance to ±25% instead of ±10%.** Rejected: at ±25% the 5,448 and 7,400 cohorts
  nearly touch, which would silently merge the two populations ADR-063 created. 10% keeps them
  separate by construction — a 5,448-bar row is 26% away from a 7,400-bar null.
- **Rescale the null's Sharpes to the pool's length analytically.** Rejected: the null's dispersion
  is measured, not modelled, and the whole point of ADR-036/051 is to avoid substituting a formula
  for a measurement. Subsetting keeps every number empirical.

## Consequences

- The report will state a real comparison again, on ~2,400 matched experiments, for the first time
  since ADR-052 introduced the fingerprint — while the **legacy-unspecified family reason keeps it
  refused until the pool turns over.** This ADR removes one of the two reasons, not both, and it
  removes the one that was never load-bearing.
- Two comparisons can now be reported at once from one pool: a 5,400-bar null against the legacy
  cohort and a 7,400-bar null against the ADR-063 cohort, each with its own `matched_n`. That is a
  strictly better description of a pool in transition than any single median could give.
- `matched_n` shrinks as the pool turns over, and when it falls under 30 the comparison is refused
  with a stated reason rather than reported quietly on a thin sample.
- The tolerance is a judgement call and is named as a constant so it can be argued with, rather than
  buried in an expression.

## How to reverse

Restore the `median_n_bars != null_bars` branch in `_mismatch`, drop `matched_n` / `matched_n_bars`
and the `experiments` argument. No stored artifact is affected in either direction: this changes
only which rows a report reads, never what any run records.

## Amendment (same day, before implementation landed): the family test moves to the subset too

§Decision item 5 said the search-family check was unchanged. Implementing the rest made that
position incoherent and it is hereby revised: **the family test is evaluated over the matched
subset, not over the whole pool.**

The reasoning is the one this ADR already makes on the history side. Once the real median is taken
over a subset, refusing the comparison because of rows *outside* that subset describes a comparison
nobody made. The test itself is untouched — a fingerprint is still an identity, and a matched subset
spanning two fingerprints is still refused (`test_a_matched_subset_spanning_two_families_is_still_refused`).
Only its population changes, to the population being compared.

It is not a formality on this pool. Measured at implementation time: the 2,427 history-matched
experiments are **100% `3f36fda2…`** — the null's own fingerprint — while all 227
`legacy-unspecified` rows carry no `n_bars` at all and are therefore already outside the subset by
rule 4. The pool-wide test was refusing a valid comparison on account of rows that could never have
been in it.

## Measured — the first formally valid real-vs-null comparison this project has produced

With both halves of `_mismatch` reading the matched subset, `scripts/pool_report.py` prints a
verdict instead of a refusal, on 2,427 matched experiments at a median 5,445 bars against nulls at
5,400:

| statistic | null | real median | null median | null p95 | verdict |
|---|---|---|---|---|---|
| walk-forward | bootstrap:SPY | **+0.542** | +0.652 | +0.983 | does not separate |
| walk-forward | iid_normal | **+0.542** | +0.414 | +0.796 | does not separate |
| purged-CV | bootstrap:SPY | **+0.584** | +0.661 | +1.003 | does not separate |
| purged-CV | iid_normal | **+0.584** | +0.475 | +0.803 | does not separate |

**The pool does not separate from either null on either statistic**, and against the bootstrap null
— which preserves SPY's fat tails, gaps and realized volatility while destroying serial structure —
the real median is *below* the null's median. This is the same conclusion the deflation headline
reaches by a different route (0 of 40 graduates clear the ADR-018 bar), now stated as a measurement
rather than as an absence of one.

Note the subset matters: the pool-wide walk-forward median is +0.567 and the matched one is +0.542.
Reporting the former against a 5,400-bar null would have been the exact error this ADR removes.

### Provenance of those four numbers, and what the report prints today

The table above was measured against the null artifacts as they stood at commit **`dbba1ed`**
(`n_bars` 5,400, fingerprint `3f36fda2…`) — verified reproducible from that ref: bootstrap
walk-forward median +0.652 / p95 +0.983 and purged-CV +0.661 / +1.003, iid-normal +0.414 / +0.796
and +0.475 / +0.803. **ADR-063's re-dispatch overwrote `data/null_calibration/*.json` with the
7,400-bar run (`6efcb7e`) hours later**, so those numbers are no longer reproducible from the
working tree, only from that ref. This is ADR-058's rule biting on its own terms — *a matching
fingerprint licenses reusing a measurement, not reusing a file that has since been overwritten* —
and it is recorded here rather than left for a future session to rediscover.

**What the report prints today is `0 matched`, and that is correct.** The pool's rows are at ~5,445
bars and the current null is at 7,400 — 26% apart, well outside `HISTORY_TOLERANCE` — so every
comparison is refused with `no experiment's history is within 10% of the null's 7400 bars` and the
row falls back to the pool-wide median. The pool and its null are genuinely out of sync until the
daily discovery re-searches the universe at ADR-063's window. **The verdict above is therefore a
statement about the pool as it was searched, not a claim the tree can re-derive right now**, and
this ADR's mechanism — not its measurement — is what changed permanently.

Keeping both lengths on disk so a pool in transition could be read against each (this ADR's
§Consequences) needs the null artifacts named by their history length; the workflow writes one file
per mode. That is a separate decision and is deliberately not smuggled in here.
