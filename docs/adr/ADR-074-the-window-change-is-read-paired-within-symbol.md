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

**347 symbols have been searched under the same family at both windows** (~5,448 bars before
ADR-063, ~9,232 after), so the comparison can be made *within symbol*, taking each symbol's median
across its repeat runs at each window. Measured 2026-08-31:

| paired delta (long window − short window), n = 347 symbols | median | 95% CI (bootstrap, 20k) | mean | SE |
|---|---|---|---|---|
| finalist **walk-forward OOS** Sharpe | **−0.041** | **[−0.070, −0.015]** | −0.048 | 0.015 |
| finalist **in-sample observed** Sharpe | +0.010 | [−0.008, +0.030] | +0.049 | 0.014 |

The out-of-sample delta is negative on 59% of symbols and its interval excludes zero; the in-sample
delta's does not. The search also picks a **different finalist strategy on 244 of the 347 symbols**.
That is the shape the anachronism risk predicts: in-sample selection unchanged or marginally better,
out-of-sample selection slightly worse, with the choice itself moving.

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
   zero.** On the confounded surrogate above the delta's SE is 0.015, so an effect of the size seen
   (−0.041) is resolvable at n ≈ 40–350; the criterion is not being stated at a sample size that
   cannot see it, which is the failure ADR-070 recorded.
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
