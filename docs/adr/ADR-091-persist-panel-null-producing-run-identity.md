# ADR-091: Persist the panel-null producing workflow run identity

- **Status:** Accepted
- **Date:** 2026-09-14
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Acts on:** FINDING-027
- **Extends:** ADR-081, ADR-083, ADR-087, ADR-089, ADR-090

## Context

The panel-null cohort records the source digest and executed git revision. ADR-089/090 additionally
identify final and scratch artifacts by `(run_id, run_attempt)`, but that pair exists only in names,
workflow inputs, and transient GitHub metadata. `PanelNullCalibration` drops it when the measurement
is committed to the ADR-030 generated-data path.

Run attempt is methodology-relevant because ADR-087 permits a full rerun only before consolidation
and forbids a second look after a final artifact exists. The durable record must remain auditable
after Actions artifacts expire.

## Options considered

1. **Rely on artifact names and workflow logs.** Rejected: the final artifact expires after 30 days,
   and external logs are not part of the validated committed measurement.
2. **Put the run identity only in the generated commit message.** Rejected: commit text is outside
   the Pydantic artifact boundary and can drift from the bytes it describes during recovery.
3. **Freeze the producing run identity in `PanelNullCohort`.** Chosen: the cohort already carries
   the exact code, source, policy, and statistical identity inherited by every shard and the final
   artifact.

## Decision

Add required positive `workflow_run_id` and `workflow_run_attempt` fields to `PanelNullCohort`.
The preparation command requires both explicitly, and the workflow passes `GITHUB_RUN_ID` and
`GITHUB_RUN_ATTEMPT` before writing the immutable manifest/source pair. Every shard and the final
calibration inherit them through the existing exact cohort identity and merge validation.

Publish-only recovery must require the authoritative metadata ID and attempt, the requested ID and
attempt, and the calibration cohort's embedded ID and attempt all to agree before creating a parent
directory or temporary destination. Existing repository/workflow/event/status/head-SHA and
canonical-byte checks remain.

The measurement is unspent, so there is no legacy artifact to migrate. No panel index, seed,
statistic, inference input, search policy, gate, or validation threshold changes.

## Consequences

- The committed measurement permanently identifies the workflow run attempt that produced it.
- Cross-attempt mixing fails at the model identity boundary as well as at artifact selection.
- Local deterministic fixtures must state an explicit synthetic run identity.
- A full pre-consolidation rerun produces a distinct cohort identity, matching ADR-087's procedure.

## Reversal

Removing the fields restores FINDING-027 and is unsafe after the fixed measurement has been spent.
