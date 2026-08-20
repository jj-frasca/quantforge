# ADR-053: Commit the power calibration record, and show it beside the Type-I error

- **Status**: Accepted
- **Date**: 2026-08-20
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Extends**: ADR-041/042 (power calibration), ADR-036/037 (null calibration), ADR-030 (single writer for generated data)
- **Relates to**: ADR-045 (capture efficiency), ADR-049 (gate attribution), ADR-051 (measure at the hunt's history)

## Context

`null-calibration.yml` consolidates its shards and **commits** `data/null_calibration/*.json`, so
the measured Type-I error is durable, readable by `scripts/pool_report.py`, served by
`GET /api/v1/null-calibration`, and shown on the dashboard's `GateCalibrationPanel`.

Neither power workflow does any of that. `power-calibration.yml` and
`horizon-power-calibration.yml` upload their per-cell JSON as GitHub Actions artifacts with a
retention window and post a Slack summary. Nothing is committed. The consequence is that the
project's power numbers exist in exactly two places: a chat message, and prose that a session typed
into an ADR by reading an artifact before it expired.

That is worse than it sounds, because power is the number that decides how the headline result is
read. "0 of 40 graduates clear the bar" is a statement about the strategies only if the gate can
detect an edge that is there; ADR-051 showed today how easily a power number goes wrong, and how
much turns on it. A measurement that cannot be re-read cannot be re-checked, and the whole point of
this project is that its claims are checkable.

There is also an asymmetry that makes the dashboard actively misleading. It shows the Type-I error
under a heading about what the gate has been measured to do, and shows nothing about power — so the
one visible number is the one that only ever says "the gate rejects things".

## Decision

**Both power workflows consolidate their cells into a committed artifact, and the API and dashboard
serve it beside the Type-I error.**

1. `scripts/consolidate_power_calibration.py` reads a directory of per-cell `PowerCalibration` JSON
   and writes one sorted list. Cells are NOT merged into a single record: unlike null shards, each
   cell plants a different process at a different effect size and is judged at its own N, so there
   is nothing to pool (the same reasoning ADR-042 used to leave the sweep unsharded).
2. `data/power_calibration/ar1.json` (swept by phi) and `data/power_calibration/band_reversion.json`
   (swept by half-life), each written by exactly one workflow — ADR-030's single-writer rule.
3. `GET /api/v1/power-calibration` returns both series, and the dashboard panel that already states
   the Type-I error states the power curve next to it.

## Alternatives considered

- **Leave it in artifacts and keep transcribing into ADRs.** Rejected: that is how a superseded
  number survives. Today's session had to correct two ADRs and the README because a stale power
  figure had been copied forward by prose.
- **Merge the cells into one `PowerCalibration` like `merge_calibrations` does for null shards.**
  Rejected as unsound. Null shards are draws from one experiment; power cells are different
  experiments. Pooling them would produce a detection rate for no stated effect size.
- **Extend the null artifact to hold power too.** Rejected: `null_mode` and `phi`/`half_life` index
  different sweeps, and one file written by two workflows breaks ADR-030.
- **Store only the summary rates, not the full records.** Rejected. The per-symbol oracle Sharpes,
  finalist Sharpes and gate pass counts are what let a later session re-derive capture (ADR-045) and
  attribution (ADR-049) without re-running. They are small — 50 floats per cell.

## Consequences

- Two new generated files under `data/`, each with exactly one writer. They accumulate history in
  git rather than expiring.
- A session can answer "what is the gate's power" by reading a file, with no dispatch and no wait.
- The dashboard states both error rates, which is the honest pair. A visible Type-I error beside an
  invisible power number reads as strength when it is only conservatism.
- The workflows gain `contents: write` and a push step, which is the same trust the null and
  discovery workflows already have.

## Reversal

Delete `data/power_calibration/`, the consolidation script, the commit steps, the endpoint and the
panel section. The workflows' measurement steps are untouched by all of it, and the artifacts keep
uploading exactly as they do now.
