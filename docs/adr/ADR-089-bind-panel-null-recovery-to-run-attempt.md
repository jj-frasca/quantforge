# ADR-089: Bind panel-null recovery to one workflow-run attempt

- **Status:** Accepted
- **Date:** 2026-09-13
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Acts on:** FINDING-025
- **Extends:** ADR-087, ADR-088

## Context

ADR-088 validates the source workflow run's authoritative repository, run ID, workflow path,
event, completion state, and head SHA. GitHub reruns retain the same run ID and head SHA while
incrementing `run_attempt`.

The artifact client permits same-named artifacts from different rerun attempts. A cross-run lookup
by name returns the latest match. The current final artifact name and recovery input contain only
the run ID, so ADR-088 proves the workflow but not the attempt that produced the downloaded bytes.
That ambiguity is unacceptable for ADR-081's fixed one-look measurement.

## Options considered

1. **Continue selecting the latest same-named artifact.**
   - Pro: no workflow input or name change.
   - Con: artifact selection can change after a rerun while all current provenance checks pass.
2. **Download by artifact database ID.**
   - Pro: globally identifies one stored object.
   - Con: the standard download action exposes name/run lookup, and an opaque ID alone does not
     state the workflow attempt in the scientific recovery procedure.
3. **Name and validate the workflow attempt explicitly.**
   - Pro: makes production, download, and authoritative metadata agree on one human-auditable
     `(run_id, run_attempt)` identity.
   - Con: recovery requires one additional input and uses the attempt-addressed API endpoint.

## Decision

Choose option 3. Consolidation names the final artifact
`panel-null-measurement-<run_id>-<run_attempt>`. Recovery requires both `recovery_run_id` and
`recovery_run_attempt`; supplying exactly one is invalid.

Recovery fetches authoritative metadata from
`GET /repos/$GITHUB_REPOSITORY/actions/runs/$RECOVERY_RUN_ID/attempts/$RECOVERY_RUN_ATTEMPT` and
downloads the exact attempt-qualified artifact name. `recover_panel_null.py` requires metadata
`run_attempt` to equal the requested positive attempt before creating a destination parent or
temporary file. ADR-088's repository, workflow, event, completed status, and head-SHA checks remain.

This decision binds recovery identity. It does not authorize rerunning after a final artifact
exists; ADR-087's stage-aware one-look rule remains unchanged.

## Consequences

- A later rerun cannot silently redirect the same recovery inputs to newer same-named bytes.
- Recovery invocations and artifact names identify the exact producing attempt in logs and UI.
- Old unqualified artifacts do not exist because the measurement remains unspent; no migration or
  compatibility branch is needed.
- ADR-090 separately applies the same attempt identity to frozen inputs and scratch shards used
  before consolidation.
- ADR-091 persists the producing run and attempt inside the durable calibration rather than leaving
  them only in ephemeral artifact names and recovery inputs.
- No seed, statistic, inference input, validation threshold, generated artifact, or measurement
  changes.

## Reversal

Remove the attempt input and suffix and return to run-only lookup. That restores FINDING-025 and is
unsafe once any source run has more than one attempt.
