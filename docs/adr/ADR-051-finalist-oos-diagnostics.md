# ADR-051: Read the out-of-sample diagnostics off every search finalist, and give the null the hunt's history

- **Status**: Accepted
- **Date**: 2026-08-20
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Extends**: ADR-038 (walk-forward efficiency), ADR-039 (purged-CV evaluation), ADR-036/037 (null calibration)
- **Relates to**: ADR-033 (pool reporting), ADR-044 (calibration identity), ADR-046 (whole-search trial accounting)

## Context

ADR-038 and ADR-039 added a walk-forward and a purged-CV out-of-sample Sharpe to every trial, and
set a revisit trigger: **compare the pool's values against `data/null_calibration/*.json`, the same
statistics measured on symbols with no edge by construction.** Three sessions have carried that
trigger forward as their handoff task and none could execute it, because `summarize_pool` reads the
diagnostics off `passing_finalists` — the finalist trial of experiments that produced a graduate —
and no graduate existed that was young enough to carry the fields.

ADR-046 landed overnight and made that permanent rather than temporary. Pricing the whole searched
hypothesis family raised the median `lifetime_trials` of a discovery experiment from 35 to 200, and
the 2026-08-20 run produced **0 graduates from 603 experiments** (08-19, same universe, same
catalog: 14). That is the correct answer to a repaired denominator, not a broken funnel. But it
means the gate-passer set is empty, the OOS diagnostic is structurally unreachable, and the report
prints `not measured (pre-ADR-038/039 pool)` — which blames the pool's age for what is really "no
experiment passed the gate". The diagnostic goes dark at exactly the moment it is most informative.

Meanwhile the statistic the null artifacts record is not the gate-passer's at all. `calibrate_gate`
records `walk_forward_oos_sharpes` for **every searched null symbol**, graduate or not — 200 values
against 0 graduates. So the pool side of the comparison was restricted to a set the null side never
was. The two halves of ADR-038's own trigger were never the same statistic.

There is a second, quieter mismatch. `scripts/null_calibration.py` fixes `N_BARS = 3000` under a
comment reading *"Matches the shape a real hunt sees: ~12 years"*. `scripts/shard_hunt.py` starts at
`2005-01-01`, so a real name carries roughly **5440 bars (~21.6 years)** — the 08-19 graduates'
median holdout of 1088 bars is 20% of 5440, which pins it. The null is judged on 55% of the history
the hunt gets. Sharpe estimates are noisier on shorter series, so the null's dispersion is inflated
relative to the pool's, and every real-versus-null reading inherits an argument.

## Decision

**1. Report the OOS diagnostics over the finalist of every experiment, and report the gate-passer
subset separately when it is non-empty.**

`PoolReport` gains `walk_forward_finalists` / `purged_cv_finalists`, summarized over
`max(e.trials, key=deflated_sharpe)` for every experiment that has trials — the same per-symbol
finalist the null artifacts record. The existing `walk_forward_graduates` /
`purged_cv_graduates` fields keep their meaning and are still reported, because "did the strategies
we actually promoted hold up" is a real and different question; they are simply no longer the only
window onto the statistic.

**2. Say which of the three states the report is in.** `no experiment carries it (pre-ADR-038/039)`,
`no experiment passed the gate` and `median … over N finalists` are three different facts and the
report must not print the first when the third is true.

**3. Judge the null on the hunt's history.** `n_bars` becomes a driver argument and a recorded field
on `NullCalibration`, defaulting to the hunt's span rather than to 3000, so an artifact
self-documents the length it was judged at and old artifacts read back as `None` instead of
silently claiming the new default.

## Alternatives considered

- **Wait for graduates to reappear.** Rejected. Under ADR-046's denominator this may not happen for
  months, and possibly not at all at the current design — ADR-043 already computed that an edge must
  be a true annualized Sharpe of 2.13 to clear the ADR-018 bar 80% of the time. A diagnostic whose
  precondition is the very event it was built to interrogate is not a diagnostic.
- **Keep gate passers primary and add finalists as a footnote.** Rejected for the same reason, and
  because the finalist series is the one that is literally comparable to the null artifact.
- **Lower a threshold so graduates reappear and the diagnostic lights up.** Forbidden by charter §4,
  and it would destroy the measurement it was meant to enable.
- **Leave `N_BARS` at 3000 and note the confound in prose.** Rejected. Re-running the null is eight
  parallel shards of free cloud compute; carrying a known length mismatch through every future
  real-versus-null reading is not worth saving five minutes once.
- **Version the null artifacts by bar count (`bootstrap-5440.json`).** Rejected as premature: the
  recorded `n_bars` field distinguishes them, git history preserves the 3000-bar run, and a second
  filename axis multiplies the consolidation surface for no reader who exists yet.

## Consequences

- The revisit trigger becomes executable on every pool, permanently, and against a matched null.
- The 3000-bar null artifacts are **superseded, not deleted** (charter §4): they remain in git
  history, and the new records state their own length so the two can never be silently mixed.
- A finalist-level comparison is a weaker claim than a gate-passer-level one, and the report must
  not be read as if it were stronger. It answers "is what the search proposes distinguishable from
  what it proposes on noise", not "do our graduates work". The second question needs graduates.
- Nothing gates on any of this. No threshold, promotion rule, or paper-book decision reads these
  fields; they are reporting only.

## Reversal

Delete `walk_forward_finalists` / `purged_cv_finalists` from `PoolReport` and the finalist block
from `scripts/pool_report.py`; restore `N_BARS = 3000` as a constant and drop the `n_bars` field
(defaulted, so artifacts written under this ADR still load). ADR-038/039's original gate-passer path
is untouched throughout and continues to work the moment a graduate appears.
