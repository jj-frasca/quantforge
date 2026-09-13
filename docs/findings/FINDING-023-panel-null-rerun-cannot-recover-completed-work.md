# FINDING-023: Panel-null reruns cannot safely recover completed work

- **Severity:** High — one transient failure can either discard completed panel shards or repeat
  an already observed one-look measurement
- **Found:** 2026-09-13 by Codex hostile review of ADR-081 artifact recovery
- **Status:** Resolved by ADR-087
- **Affected:** `panel-null-calibration.yml`

## Finding

The manual panel-null workflow has one artifact per successful matrix shard, but it defines no safe
recovery path. GitHub permits re-running all jobs, failed jobs, or one job while retaining the
original `GITHUB_SHA`. Artifact v4 archives are immutable within a workflow run, and artifacts from
an earlier run attempt are not a reliable input to a later attempt. Re-running only failed batch
jobs can therefore leave consolidation with only the newly repeated shards, while re-running all
jobs recomputes all 400 panels and the observed source panel.

That distinction becomes methodology-critical after consolidation. The existing job uploads the
complete measurement before its three-attempt git push. If the push alone fails, the fixed result
already exists and may have been inspected. Re-running computation would spend another look instead
of publishing the exact completed artifact.

## Evidence

- The matrix uploads 100 immutable `panel-null-shard-N` artifacts and consolidation downloads them
  from the current workflow run, with no recovery mode or source-run identifier.
- GitHub documents that a rerun retains the original `GITHUB_SHA`/`GITHUB_REF`, but offers distinct
  full, failed-job, and single-job reruns; the workflow does not state which is valid.
- `actions/upload-artifact` documents that v4 artifacts are immutable and a repeated name fails by
  default. Its public issue tracker records prior-attempt artifacts becoming inaccessible after a
  workflow retry even when names include the attempt number.
- The final `panel-null-measurement-<run_id>` artifact is retained for 30 days, but no workflow path
  can validate and publish those exact bytes without regenerating the statistic.

## Impact

A transient runner or push failure can waste most of the 400-panel computation. More seriously, a
push-only failure can tempt an operator to rerun an experiment whose inference is already visible,
violating ADR-081's fixed one-look rule. The measurement remains unspent, so no existing artifact
or headline is affected.

## Required correction

Keep ordinary execution unchanged, but add an explicit publish-only recovery mode to the same
manual workflow. It must download the named final measurement artifact from one prior run, fully
validate the `PanelNullCalibration`, copy those exact canonical bytes to the sole-writer path, and
commit without running preparation, batches, or inference again. Normal and recovery modes must be
mutually exclusive. Documentation must state that pre-consolidation failures require a full rerun,
whereas any failure after final-artifact upload must use publish-only recovery and never recompute.

## Resolution

ADR-087 adds that mutually exclusive recovery mode to the same manual workflow. It downloads the
30-day final artifact by prior run ID, validates the complete panel/calibration identity before
touching the destination, rejects bytes that are not the canonical serialization of that validated
model, atomically preserves the exact accepted bytes, and commits through the existing sole-writer
retry path. Preparation, batches, and consolidation are skipped in recovery mode.
