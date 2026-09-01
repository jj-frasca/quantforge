# FINDING-017: Purged-CV excess is now measured

- **Severity:** Informational — new methodology evidence, no gate or threshold defect
- **Found:** 2026-09-01 by Codex review of daily discovery commit `873558a`
- **Status:** Measured; governed narrative updated
- **Affected:** `scripts/pool_report.py`, ADR-078 evidence, architecture and validation cold memory

## Finding

The first daily discovery refresh after ADR-078 populated `purged_cv_hold_sharpe` on enough of the
7,400-bar real cohort to make the drift-controlled comparison measurable. The report now has 254
history-matched experiments, of which 88 symbols carry both the selected finalist's purged-CV OOS
Sharpe and the same series' buy-and-hold Sharpe over the kept folds.

The real paired excess median is effectively zero (`-0.000`). Against the bootstrap null, whose
median is also `-0.000`, the symbol-clustered difference of medians is
`+0.000 [-0.048, +0.002]`. Against iid-normal it is `+0.000 [-0.048, +0.000]`. Both intervals span zero.
The result therefore supplies no evidence that purged-CV selection adds performance beyond holding
the same series, and no evidence that the real excess differs from the null excess.

This is distinct from the raw purged-CV level: the matched real median is `+0.601`, versus `+0.639`
on the bootstrap null and `+0.442` on iid-normal. Subtracting each series' own drift collapses those
levels to the paired quantity ADR-078 intended.

## Artifact audit

Commit `873558a` was a genuine current-universe refresh rather than only a formatter rewrite. It
replaced 601 prior experiment identities, added 602 current identities (including a new `COO`
experiment), retained 2,656 historical identities, and moved the pool from 3,257 to 3,258
experiments over 607 symbols. On retained experiments it changed no existing value; model
serialization added only `selected_trial_index` and `purged_cv_hold_sharpe` to the 2,631 historical
records that predated those nullable fields.

## Consequence

The former `NOT MEASURED` narrative was correct before this artifact cycle but became stale when
the refresh landed during the ADR-080 delivery race. Documentation now records the measured result.
Nothing gates on this diagnostic, no threshold moves, and generated `data/*.json` remains untouched
by this correction.
