# FINDING-024: Panel-null recovery trusts artifact self-identity

- **Severity:** High — publish-only recovery can make an internally consistent artifact part of
  the scientific record without proving which workflow run produced it
- **Found:** 2026-09-13 by Codex hostile review of ADR-087 recovery provenance
- **Status:** Resolved by ADR-088
- **Affected:** `panel-null-calibration.yml`, `recover_panel_null.py`

## Finding

ADR-087 downloads `panel-null-measurement-<recovery_run_id>` with an Actions-read token and
validates the contained `PanelNullCalibration`. That proves the artifact is complete and internally
consistent, but it does not bind the artifact to GitHub's record of the source run.

`actions/download-artifact` intentionally permits cross-run downloads when `run-id` and a token are
supplied. The selected run ID can identify any workflow run in the repository. An artifact can
self-report any valid 40-character `cohort.code_revision`; recovery currently never checks that
value against the source run's actual `head_sha`, nor does it prove that the run executed
`.github/workflows/panel-null-calibration.yml` via `workflow_dispatch`.

## Evidence

- The recovery input is interpolated directly into `actions/download-artifact@v4` as `run-id` and
  into the artifact name.
- The recovery command receives only the downloaded JSON and destination path. It has no trusted
  source-run metadata to compare with `cohort.code_revision`.
- GitHub's `GET /repos/{owner}/{repo}/actions/runs/{run_id}` response supplies the authoritative
  `id`, `path`, `event`, `status`, `head_sha`, and repository identity needed for this binding.
- No other current workflow emits the same artifact prefix, but that repository convention is not
  an enforced provenance boundary and can drift later.

## Impact

A mistyped or eventually colliding run ID normally fails on the artifact name, but a matching
artifact from an unintended workflow would pass the scientific model and be committed as the fixed
panel-null result. Its embedded code revision would be a claim made by the payload rather than one
verified against the execution system. The 400-panel measurement remains unspent, so no existing
artifact is affected.

## Required correction

Before touching the generated destination, fetch the selected source run's metadata from GitHub's
Actions API and require the exact current repository, workflow path, `workflow_dispatch` event,
completed status, requested run ID, and `head_sha == cohort.code_revision`. The recovery script must
own this check so tests can exercise it without network access; the workflow supplies the trusted
API response as an input artifact.

## Resolution

Resolved by ADR-088. Recovery now fetches the selected run through GitHub's read-only Actions API
and the recovery script validates its repository, requested ID, workflow path, manual event,
completed state, and `head_sha == cohort.code_revision` before creating or replacing the generated
destination. Focused regression coverage proves every identity mismatch preserves an existing
destination unchanged.
