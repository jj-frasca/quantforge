# ADR-074: Read the ADR-063 window change paired within symbol

- **Status**: Accepted
- **Date**: 2026-08-31
- **Deciders**: Autonomous session #15 (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-063 (extend the search history), whose second clause this answers
- **Relates to**: ADR-068/072 (the drift confound), ADR-052/064 (search-family identity),
  ADR-070 (state the standard error before the criterion)

## Context

ADR-063 extended `SEARCH_HISTORY_START` to 1990 and pre-stated what would show it was wrong:
**detection at the dead cells must rise, or the pool's median holdout Sharpe must not fall.** The
first clause was measured on 2026-08-29 and failed for a reason ADR-063 records. The second was left
open "until the daily discovery has re-searched the universe at the new window". The re-search has
happened. The clause still cannot be read, and the reason is not that more data is needed.

**The statistic it names does not exist at a readable sample size.** A holdout Sharpe is recorded on
a `Graduate`, i.e. only on an experiment that passed the gate. The pool holds 221 graduate
experiments and **220 of them carry `search_config_version = legacy-unspecified`** — written before
ADR-052, so their search family cannot be reconstructed and ADR-064's identity rule refuses to
compare them. Under the live family `3f36fda2…` the pool has **exactly one** graduate in 3,029
experiments. There is no median to take, and the gate's own strictness is why.

This is the third criterion in this project phrased over a quantity nobody had sized first —
ADR-063's own first clause was phrased over cells with nothing to find, ADR-070's over per-cell
rates whose standard error was three times any plausible effect, and this one over a sample the gate
produces at a rate of 1 in 3,029. **The pattern is now the rule, not the exception.**

## The measurement that is available, and it is a paired one

The concern §Consequences actually named was *selection quality*: 1990s costs are anachronistic, so
the longer in-sample window may make the search prefer configurations that traded a market that no
longer exists. That is a statement about the finalist the search picks, which every experiment
records — not about the graduates, of which there are none.

**368 symbols have been searched under the same family at both windows** (median ~5,446 bars before
ADR-063, ~9,232 after), so the comparison can be made *within symbol*, taking each symbol's median
across its repeat runs at each window. Measured 2026-08-31, and reproducible from a checkout with
`PYTHONPATH=. uv run python scripts/pool_report.py`:

| paired delta (long window − short window), n = 368 symbols | median | 95% CI (bootstrap, 20k, seed 7) | mean | SE |
|---|---|---|---|---|
| finalist **walk-forward OOS** Sharpe | **−0.038** | **[−0.060, −0.009]** | −0.042 | 0.015 |
| finalist **in-sample observed** Sharpe | +0.012 | [−0.005, +0.034] | — | — |

The out-of-sample delta is negative on 57.6% of symbols and its interval excludes zero; the
in-sample delta's does not. The search also picks a **different finalist strategy on 257 of the 368
symbols**. That is the shape the anachronism risk predicts: in-sample selection unchanged or
marginally better, out-of-sample selection slightly worse, with the choice itself moving.

**It is not yet the answer, for a reason ADR-068 already established.** The two sides' walk-forward
OOS Sharpes are computed over different calendar windows — the long side's folds reach into the
1990s — and that statistic is denominated in the drift of the window it was measured on. A −0.041
difference in drift between 1990–2005 and 2005–2026 would produce this entire result with no change
in selection quality at all. The pre-ADR-063 rows predate ADR-068's paired benchmark, so the drift
cannot be differenced out of them. **More pool rows will never fix this**; only a deliberate
re-search at the old window with the benchmark recorded will.

## Decision

1. **ADR-063's second clause is restated**, and the original phrasing is recorded as unanswerable
   rather than quietly reinterpreted: the pool's median *holdout* Sharpe cannot be read under the
   live search family, because the family has produced one graduate.
2. **The window change is judged paired within symbol on the finalist's walk-forward excess over
   buy-and-hold** (ADR-068), which is the same statistic on both sides with each side's own drift
   removed. `compare_search_windows` computes the paired deltas from the pool and the CLI report
   prints them, so the readout is reproducible from a checkout and updates itself.
3. **The criterion is stated here, before the decisive measurement exists.** A sample of ≥ 40
   symbols is re-searched at `SEARCH_HISTORY_START = 2005-01-01` with `walk_forward_hold_sharpe`
   recorded, and paired against the same symbols' live long-window rows. **ADR-063's window is
   revisited only if the paired median excess delta is negative AND its bootstrap 95% CI excludes
   zero.** On the confounded surrogate above the per-symbol delta's SD is ≈0.29, so at n = 40 the
   SE of the mean is ≈0.046 — larger than the −0.038 seen, which means **n = 40 can only resolve an
   effect roughly twice that size, and a null result at n = 40 must be reported as inconclusive
   rather than as a pass.** Stating that now is the point: it is the sizing ADR-070 recorded twice
   as missing.
4. Nothing is reverted on today's evidence. ADR-063's window stays.

## Alternatives considered

1. **Read the clause as written and report "no graduates, therefore not falsified."** Rejected: it
   is a criterion that can never fail, which is worse than one that failed.
2. **Compare history cohorts across symbols instead of within them.** Rejected, and it was measured
   before being rejected: under the live family, `n_bars` varies mostly with a symbol's listing age,
   and the < 6,000-bar and ≥ 6,000-bar cohorts share **zero symbols**. That comparison is between
   young companies and old ones, not between two windows.
3. **Substitute the raw walk-forward OOS delta and act on it.** It is the table above, and acting on
   it would be acting on a drift difference. It is reported, with the confound named, and it is not
   the criterion.
4. **Revert `SEARCH_HISTORY_START` now, on the surrogate.** Rejected: ADR-063 bought a measured
   reduction in the resolution bar (2.13 → 1.82 as the pool re-searches) and a measured rise in
   detection in every AR(1) cell with an edge to find. Trading that for a −0.041 that a drift
   difference could fully explain is not a trade this evidence supports.

## Consequences

- The pool report gains a section that reads the ADR-063 window change directly, and it will read it
  on the drift-controlled statistic the moment both sides of a symbol carry the benchmark.
- The project has a concrete, cheap, pre-registered experiment to run rather than an open clause.
- ADR-063's first clause stays failed and its second stays open; neither is reinterpreted.

## Reversal

Drop `compare_search_windows` and its report section. ADR-063's second clause then returns to being
open and unanswerable, which is the state this ADR found it in.

## Measured (2026-08-31, same session) — the criterion was applied as stated and it FAILS

> **Correction (2026-08-31, session #16 — FINDING-013).** The two sentences below that call 45 the
> whole candidate pool are wrong. The candidate set held **368** symbols when this was written and
> holds 368 today; `window_experiment.py 45` searched 45 because 45 was its argument. The reading
> and the decision stand exactly as recorded — the criterion was applied as pre-stated and did not
> fire — but the *reason* for stopping at 45 was a misreading, and "re-run when the pool reaches
> ~75" is void. **ADR-076 supersedes the closing instruction**: it freezes a sample of 200, sizes it
> from the dispersion measured here, and reads it under a two-look Pocock boundary.

`PYTHONPATH=. uv run python scripts/window_experiment.py 45` re-searched **45** symbols that
carry ADR-068's benchmark at the long window and not at the short one, at
`PRE_ADR063_SEARCH_START = 2005-01-01`, full 34-strategy catalog, 100% yield, median 5,448 bars.
The comparison and its sample are committed at `data/window_experiment/adr074_summary.json`;
the ~1 MB raw store beside it is refused by the repo's large-file hook and stays local.

| paired delta (long − short), n = 45 symbols | median | 95% CI (bootstrap 20k, seed 7) | mean | SE |
|---|---|---|---|---|
| **drift-controlled excess** — *the criterion* | **−0.074** | **[−0.157, +0.030]** | −0.086 | 0.032 |
| raw walk-forward OOS — the surrogate | −0.038 | [−0.060, −0.009] | — | 0.015 |

**The interval includes zero, so the criterion does not fire and ADR-063's window stays.** That is
the decision, applied exactly as pre-stated, and it is recorded before anything is argued around it.

Three things the run did establish:

1. **The drift confound does not explain the surrogate.** Decision 3 existed because a
   1990-vs-2005 drift difference could have produced the whole −0.038. It did not: with each side
   differenced against holding its own series over its own windows, the point estimate is **−0.074**
   — twice the surrogate's magnitude, same sign, negative on 60% of symbols. Removing the confound
   made the effect larger, not smaller.
2. **The sizing warning written into decision 3 was correct, and it is why this is inconclusive
   rather than a pass.** The interval's half-width is 0.093, about 2.4× the surrogate effect.
   Resolving −0.074 on this estimator needs **n ≈ 75** at 95%, and ≈200 at the two-look boundary
   ADR-076 applies. ~~the candidate pool held exactly 45 today~~ — see the correction above: it held
   368.
3. **The estimator mattered as much as the threshold.** The same 45 deltas give a mean of −0.086
   against an SE of 0.032 — 2.7 standard errors from zero, which *would* have fired a criterion
   stated on the mean. The criterion was stated on the median before the data existed, so the median
   is what governs. **The lesson to carry forward is to pre-state the ESTIMATOR, not only the
   threshold, and to prefer the one with the tighter interval when both are defensible** — a median
   with a bootstrap interval is robust but costs roughly 1.6× the sample of a mean.

~~**Re-run the same command when the candidate pool reaches ~75 symbols.**~~ **Void — see the
correction above.** The candidates were already there, and "the same command" does not reproduce
the same experiment: the shuffle is over the *current* candidate list, so a growing pool re-rolls
which symbols are in the sample. **ADR-076 carries this forward** with the sample frozen to a
committed artifact, n = 200, and the second look read at a Pocock boundary.
