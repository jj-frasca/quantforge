# FINDING-352: The committed score archive cannot yet support full-gate geometry

- **Status:** Measured input-readiness shortfall; no new market experiment
- **Date:** 2026-11-13, Codex W46 session21
- **Governs interpretation:** ADR029/095/417/418/424/425; complements FINDING351
- **Evidence:** [fixed contract and reproduction](../evidence/FINDING-352/README.md),
  [complete vintage inventory](../evidence/FINDING-352/vintages.json)

The biggest demonstrated obstacle to an honest quality/value portfolio gate is
causal input history, alongside complete price-source coverage. The new November8
fundamental sweep adds a vintage, but does not unlock the requested experiment.
This finite offline audit quantifies the geometry constraint previously recorded
qualitatively in FINDING351. It does not repeat any portfolio or SIC study.

## Fixed question and scope before enumeration

Can the committed fundamental-score archive at
`f30dda6987dff8ec8a705ec5ab8922de20d07d5c` alone supply the unchanged252-search plus
252-holdout daily geometry by November13? Inventory ALL path-changing revisions,
without score-based selection. Compare the newest revision to its predecessor
for coverage only. Even grant one possible observation on every calendar date
from the earliest snapshot through the full November13 date. If that generous
bound is below504, the archive fails a necessary condition. Passing this condition
would still not prove source/PIT validity, MinTRL, or any economic hurdle.

The14-commit count and earliest/latest dates were already known from triage;
this is retrospective feasibility accounting, not blind statistical inference.
Independent research review approved the written contract before blob enumeration.
There are zero new policies, strategy variants, price requests or economic trials.
No p-value or uncertainty interval applies to this exhaustive metadata census.
Prior technical and quality/value selection, including unpersisted/failed attempts,
remains relevant; effective N is never reset to1.

## Concrete result

All14 reachable revisions run from August18 to November8. Even assuming the
oldest scores were available throughout August18 and counting weekends, holidays
and all of November13, there are only **88 calendar dates**, **416 below504**.
Actual usable trading observations can only be fewer. No older prices can repair
this score-availability shortfall by broadcasting later scores backward.

| Snapshot | Records | Non-null combined | Extra duplicate-symbol rows | Extra duplicate-CIK rows |
|---|---:|---:|---:|---:|
| First, August18 | 3,224 | 1,574 | 0 | 0 |
| Previous, November1 | 4,260 | 3,253 | 1 | 0 |
| New, November8 | 4,260 | 3,253 | 2 | 0 |

The full inventory includes hashes and all intermediate counts. Duplicate symbols
are a separately observed identity qualification, not a resolved mapping, excluded
name or diagnosis of the underlying company. No rank, roster or cohort changed.
Git author/committer dates do not prove remote publication or original filing PIT;
even granting optimistic availability cannot overcome this date bound. This
result concerns the pinned reachable pool archive, not every possible external
historical source or all future research designs.

## Scorecard, costs and alpha verdict

At the same pin, existing read-only reports show3,314 retained experiments across
607 symbols,7,103,306 lifetime trials,279 graduate experiments and **zero of41**
universe survivors. The44 retained paper configurations have zero126-bar mature
records (maximum86 bars); median same-name return difference is **-1.82729pp**
across all44, **+9.96583pp** for7 open and **-1.91233pp** for37 closed. These unequal,
lifecycle-truncated configuration comparisons are descriptive, not funded account
alpha. Historical account costs are unverified; the current forward producer uses
0.001 per internal turnover and its holding comparator is gross (ADR413).

No new gross/net return, drawdown, turnover, exposure, benchmark excess, PBO, DSR,
walk-forward or graduation result was measured. Existing ADR418 comparison remains
fixed-unit long-only selected versus eligibleEW/SPY/cash,10bp entry and exit, with
strictly positive net excess against all three. Costs and thresholds are unchanged.
**The alpha case did not improve.** The result rejects present archive readiness,
not the quality/value hypothesis and not all possible paths to historical PIT data.

## Next concrete experiment

The next already authorized economic observation remains ADR418's ONE final
screen in **[2027-02-11T00:00Z,2027-02-12T00:00Z)**, using its sealed412 eligible,
83 selected and64 scheduled closes. Do not acquire its interim prices or compute
interim economics. A positive screen would still be a lead, not full-gate alpha.
ADR416 remains completed, ADR417 permanently UNEVALUABLE and ADR422 permanently
EXPIRED; no retry, replacement, reseal or source repair follows from this finding.

For the longer full-gate objective, preserve future published vintages through
the existing sole writer; reassess when genuinely new causal source evidence
arrives. This finding does not authorize a replacement study, longer414–416 run,
new source acquisition or another parser/account component chain.
