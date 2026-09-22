# ADR-093: Report which symbols a null artifact's history band actually reaches

- **Status**: Accepted
- **Date**: 2026-09-22
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-064 (matched-history null comparison), ADR-065 (null artifacts named by length),
  ADR-063 (the 1990 search window that made the pool bimodal)
- **Relates to**: ADR-051 (judge the null at the hunt's own length), FINDING-012 (clustering does not
  repair independence — this buys precision, not validity)

## Context

`history.py` has told every reader since ADR-063 to *"bump `CALIBRATION_N_BARS` deliberately as
history accumulates."* Nobody did, because nothing measured whether it was due — the note is
advice, not a check. This is the WIP that was going to be that check: written 2026-08-31, stashed
before it landed, and picked up three weeks later (2026-09-22) rather than left to rot further.

ADR-064 already fixed the *comparison*: it matches a null artifact against the experiments within
`HISTORY_TOLERANCE` of that artifact's own `n_bars`, so a pool spanning two history cohorts is read
against both instead of refused outright. What ADR-064 does not do is say how much of the pool
*neither* artifact reaches — a symbol that matches no null simply never appears in any
`NullComparison` row, silently. Measured today (`scripts/pool_report.py`, 3,275 experiments over 607
symbols, against the four artifacts in `data/null_calibration/`: `{bootstrap:SPY, iid_normal} x
{5400, 7400}` bars): the 5,400-bar artifacts match 63 symbols, the 7,400-bar artifacts match 91, and
**452 of 607 symbols — 74% of the pool — match no artifact at all.** The largest shared length among
those 452 is 9,247 bars: the saturation length of ADR-063's 1990-01-01 window (every symbol listed
before 1990 gets the whole window minus its holdout, so this mass grows by one bar per trading day
and was never going to intersect a fixed-length artifact on its own). That is a large, free sample —
ADR-078 established that tightening the headline excess interval is exactly what this project's
central claim needs most — sitting unused because nothing said it existed.

## Decision

**Add a standing report, `history_coverage`, printed above the null comparison in every
`pool_report.py` run: per artifact, how many symbols its tolerance band reaches, and beside it the
size and modal length of the mass that no artifact reaches.**

1. `history_coverage(experiments, calibrations)` (`app/research/lab/pool_report.py`) takes the
   longest recorded `n_bars` per symbol (a symbol searched more than once counts once — the
   comparison already clusters by symbol, ADR-075, so counting rows here would overstate what a
   dispatch would buy) and, for each calibration artifact, the count of symbols within
   `HISTORY_TOLERANCE` of that artifact's median `n_bars`.
2. `HistoryCoverage.largest_unmatched_n_bars` reports the **modal**, not median, length among the
   symbols no artifact reaches. The unmatched mass is itself bimodal-prone (everything younger than
   the window sits at whatever length it happens to be at; everything older saturates at one exact
   shared length) — a median can land in the valley between them, which is the same failure mode
   ADR-064 diagnosed in the original 5,444-vs-7,400 comparison. Taking the mode names the length a
   calibration dispatch would actually have to hit to matter.
3. `scripts/pool_report.py` prints the coverage table before the null-comparison rows, and when
   there is unmatched mass it prints the dispatch suggestion directly: *"dispatch
   `null-calibration.yml` with `n_bars=<modal>`"* — actionable, not just descriptive.
4. Experiments with no recorded `n_bars` (pre-ADR-052 legacy rows) are excluded from both the
   matched and unmatched counts, matching ADR-064 rule 4: a row that cannot state what produced it
   cannot be shown to match or fail to match anything.

## Alternatives considered

- **Fold this into `compare_with_null`'s existing `matched_n`.** Rejected: `matched_n` is per
  `(diagnostic, null)` pair and only exists for artifacts that already have a `NullComparison` row.
  A symbol matching *no* artifact never produces a row to attach a count to — the whole point is to
  surface the mass that is currently invisible.
- **Use the pool-wide median `n_bars` as the dispatch suggestion.** Rejected for the reason above:
  ADR-064 already showed a median describes neither cohort of a bimodal pool. The saturated tail is
  its own mode, and that is the number worth dispatching at.
- **Auto-dispatch a new calibration when coverage drops below a threshold.** Rejected: this project
  spends no money and no autonomous session may add a new paid or unattended-triggering workflow
  without it being reviewed as its own decision (charter §4). Printing the suggestion and leaving the
  dispatch to a human (or a future session with fresh judgement) is the reversible choice.

## Consequences

- `scripts/pool_report.py` now says explicitly when the calibration has stopped describing the pool,
  instead of that fact being discoverable only by noticing that a lot of symbols are quietly absent
  from every `NullComparison` row.
- Today's number — 452 of 607 symbols, 74% of the pool — is a call to action, not a bug: dispatching
  `null-calibration.yml` at `n_bars=9247` is additive (ADR-065 lets artifacts of different lengths
  coexist) and needs no re-search of anything already in the pool.
- This does **not** repair FINDING-012: more clusters make the confidence interval tighter, not the
  underlying symbols more independent. It buys precision on an already-measured lower bound, not
  validity beyond what ADR-075 already qualifies.
- `HISTORY_TOLERANCE` and `MIN_MATCHED` (ADR-064) are reused as-is; this ADR adds no new tunable.

## How to reverse

Delete `ArtifactCoverage`, `HistoryCoverage`, and `history_coverage` from `pool_report.py`, and the
coverage-table print block from `scripts/pool_report.py`. No stored artifact is affected in either
direction — this only changes what one script prints.

## Measured

Run 2026-09-22, `PYTHONPATH=. uv run python scripts/pool_report.py` against
`data/research_pool/` (3,275 experiments, 607 symbols) and `data/null_calibration/`'s four artifacts:

```
null artifact coverage (ADR-093 — is the calibration length still the pool's?):
  bootstrap:SPY  @ 5400 bars -- matches 63 symbols within 10%
  bootstrap:SPY  @ 7400 bars -- matches 91 symbols within 10%
  iid_normal     @ 5400 bars -- matches 63 symbols within 10%
  iid_normal     @ 7400 bars -- matches 91 symbols within 10%
  452 symbols match NO artifact; the largest shared length among them is 9247 bars -- dispatch
  null-calibration.yml with n_bars=9247 to use them (additive, ADR-065 names artifacts by length)
```
