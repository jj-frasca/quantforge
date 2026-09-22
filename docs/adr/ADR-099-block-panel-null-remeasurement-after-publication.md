# ADR-099: Block panel-null remeasurement after publication

- **Status:** Accepted
- **Date:** 2026-09-22
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Acts on:** FINDING-031
- **Extends:** ADR-081, ADR-087

## Context

ADR-081 fixes one 400-panel look. ADR-087 permits a full rerun only before consolidation and
requires exact-byte recovery after the final artifact exists. That stage distinction is currently
procedural: a rerun checks out the dispatch SHA, where the later generated commit cannot be seen,
and nothing prevents another complete inference from being computed and uploaded.

## Decision

In the workflow's input-validation job, check out the dispatch tree and, for normal mode only,
fetch current `master` into `refs/remotes/origin/master`. Before preparation starts, use Git object
existence to test for
`data/panel_null_calibration/replicated_correlated_panel_null.json` on current master. If it exists,
fail loudly and direct the operator to ADR-087 publish-only recovery.

The existing workflow concurrency group serializes dispatches, so a second queued normal run sees
the first run's published path. Recovery mode skips the prohibition because it performs no search
or inference. A future reviewed new measurement must choose and pre-register a new durable
destination as part of its new identity; it must not delete or bypass this guard.

## Consequences

- A completed result cannot be followed by an accidental normal-mode rerun that exposes a second
  look before failing to publish.
- Pre-consolidation full reruns remain possible while no generated measurement exists on master.
- Publish-only recovery remains the only path after publication.
- No seed, panel, statistic, inference rule, gate, generated data, or validation threshold changes.

## Reversal

Removing the current-master preflight restores FINDING-031 and converts ADR-087's one-look rule
back into an unenforced operator convention.
