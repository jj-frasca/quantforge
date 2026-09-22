# FINDING-027: The durable panel-null record loses its producing run identity

- **Severity:** High — after workflow artifacts expire, the committed measurement cannot identify
  which workflow run attempt produced the fixed one-look result
- **Found:** 2026-09-14 by Codex hostile review of ADR-089/090 provenance
- **Status:** Resolved by ADR-091
- **Affected:** `PanelNullCohort`, `panel-null-calibration.yml`, panel-null preparation and recovery

## Finding

ADR-089 and ADR-090 put `(run_id, run_attempt)` in GitHub artifact names and recovery inputs, but
the validated `PanelNullCalibration` committed under `data/` stores neither value. Its cohort stores
the executed git SHA and source digest, which identify code and input bytes, not the execution that
spent ADR-081's fixed one-look measurement.

Normal publication therefore drops the producing run identity as soon as the named artifact is
copied into the durable generated-data path. Publish-only recovery checks the requested run and
attempt against GitHub metadata, but it does not compare them with fields in the payload because
those fields do not exist. After the 30-day final artifact expires, the committed JSON cannot prove
whether it came from the original attempt or a later full rerun at the same revision and inputs.

## Impact

ADR-081 forbids an unpriced additional look, and ADR-087 makes rerun stage part of the scientific
procedure. A durable result that records code and source but not the execution attempt cannot audit
that rule independently of ephemeral Actions retention and logs. Artifact naming prevents service
selection ambiguity during execution; it does not preserve provenance inside the published record.

The 400-panel measurement remains unspent, so no existing generated result requires migration.

## Required correction

Freeze positive `workflow_run_id` and `workflow_run_attempt` values in the panel-null cohort before
the immutable input pair is written. Pass GitHub's current run identity into preparation, inherit it
through every shard and the final calibration, and require recovery metadata plus requested inputs
to equal the payload's embedded identity before destination mutation. Preserve all symbols, panels,
seeds, statistics, inference inputs, and validation thresholds.

## Resolution

Resolved by ADR-091. The immutable cohort now requires the positive producing workflow run ID and
attempt; preparation receives both from GitHub, all shards and the final calibration inherit them,
and recovery requires exact agreement among the payload, request, and authoritative run metadata.
