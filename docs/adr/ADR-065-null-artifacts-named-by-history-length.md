# ADR-065: Name a null artifact by the history length it measured

- **Status**: Accepted
- **Date**: 2026-08-29
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-064 (matched-history comparison), ADR-063 (the 1990 search window)
- **Relates to**: ADR-030 (single writer per generated file), ADR-051 (judge the null at the hunt's
  length), ADR-058 (a fingerprint licenses reusing a measurement, not an overwritten file)

## Context

ADR-064 made the real-vs-null comparison run on the experiments whose history matches the null
artifact's, and named the benefit explicitly in its §Consequences:

> Two comparisons can now be reported at once from one pool: a 5,400-bar null against the legacy
> cohort and a 7,400-bar null against the ADR-063 cohort, each with its own `matched_n`.

**That benefit is currently unreachable, because only one length can exist on disk.**
`null-calibration.yml` writes `data/null_calibration/${mode}.json` — a name that says which null was
used and nothing about what it was measured at — so every re-dispatch overwrites its predecessor.
The cost was paid the same day this was written: ADR-064's four headline numbers were measured
against the 5,400-bar artifacts, ADR-063's re-dispatch replaced them with 7,400-bar ones hours
later, and the published measurement is now reproducible only from commit `dbba1ed`. ADR-064 had to
carry a provenance paragraph pointing at a git ref because the tree could no longer answer.

Meanwhile the pool sits at ~5,445 bars against a 7,400-bar null — 26% apart — so `pool_report.py`
prints `0 matched` and refuses all four comparisons. The refusal is correct. **The project's
"does the search beat a no-edge surrogate?" headline is unmeasurable from the tree until the daily
discovery re-searches the whole universe, even though a valid null for the pool's actual history was
measured four days ago and is sitting in git history.**

The filename is the whole problem. Nothing else needs to change: `pool_report.py` and
`GET /api/v1/null-calibration` both glob `data/null_calibration/*.json` and read `n_bars` off each
artifact, so more files with distinct names flow through without a code change on the read side.

## Decision

**Derive the artifact's filename from the history it was measured at, and keep the superseded pair
that still matches the pool.**

1. `consolidate_null_calibration.py` takes an output **directory** and writes
   `<null_mode>_<median n_bars>.json` — `bootstrap_spy_7400.json`, `iid_normal_7400.json`. The name
   comes from the merged artifact's own `n_bars`, so it cannot disagree with its contents.
   `null-calibration.yml` passes the directory.
2. **A re-run at the same length still overwrites**, which is what should happen: that is a
   re-measurement of the same pair, not a second one. Only a genuine change of history length
   creates a new file, so the directory grows once per ADR-063-class decision and not once per run.
   ADR-030's single-writer rule is preserved — the workflow remains the sole writer of every file
   in that directory.
3. The two current files are **migrated** (`git mv`) to their 7,400-bar names, and the 5,400-bar
   pair is **restored from `dbba1ed`** under its own names. Nothing is deleted (charter §4): the
   restored pair is the null that matches the pool's actual history, and reinstating it is what
   makes ADR-064's comparison measurable from the tree again today.
4. The dashboard's `GateCalibrationPanel` gains a **History** column and keys its rows on
   `(null_mode, history)`. Two rows per mode with no visible difference between them would be worse
   than one — and the length is the reason both exist.

## Alternatives considered

- **Archive superseded artifacts under `data/null_calibration/superseded/`.** Rejected: the read
  side globs non-recursively, so an archived null is invisible to the report — it would fix
  provenance while leaving the comparison unmeasurable, which is the smaller half of the problem.
- **Keep one file per mode and re-dispatch the null at the pool's length whenever they diverge.**
  Rejected: during a transition the pool has *two* lengths at once, so no single null can match it,
  and this amounts to re-running a multi-hour calibration to chase the pool's median — the standing
  obligation ADR-064 rejected in its own §Alternatives.
- **Put the length inside the file only, and let the reader disambiguate.** That is the status quo:
  the length *is* already in the file. It does not help, because two artifacts cannot occupy one
  path.
- **Retain every run by timestamp.** Rejected: it makes the directory grow without bound and makes
  "which null is current for this length?" ambiguous — the opposite of what a matched comparison
  needs.

## Consequences

- The report reads a pool in transition against **both** cohorts, each with its own `matched_n`,
  which is exactly what ADR-064 built the machinery for and could not use.
- ADR-064's published verdict becomes reproducible from the working tree again, rather than only
  from a git ref.
- `GET /api/v1/null-calibration` returns four rows instead of two while the transition lasts. The
  response model is a list and is unchanged; the dashboard shows the length.
- A future length change adds a file rather than destroying evidence. The failure that produced
  ADR-064's provenance paragraph cannot recur in this directory.
- The power-calibration artifacts are deliberately **out of scope**. They are not matched against
  the pool — they describe the gate at one length and are superseded wholesale, with the length
  stated inside the file. If a future decision needs two power lengths side by side, it should make
  that argument on its own terms rather than inherit this one.

## How to reverse

Have the consolidation script write `<mode>.json` again, pass the file path from the workflow, drop
the History column, and `git mv` the length-named files back. No artifact is invalidated in either
direction — each one states the length it was measured at, which is the property this ADR moves into
the filename.
