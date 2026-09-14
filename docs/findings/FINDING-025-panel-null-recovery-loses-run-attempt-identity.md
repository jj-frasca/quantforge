# FINDING-025: Panel-null recovery loses workflow-run attempt identity

- **Severity:** High — one recovery run ID can resolve a same-named measurement from a different
  rerun attempt, silently changing which completed look enters the scientific record
- **Found:** 2026-09-13 by Codex hostile review of ADR-088 recovery provenance
- **Status:** Resolved by ADR-089
- **Affected:** `panel-null-calibration.yml`, `recover_panel_null.py`

## Finding

ADR-088 binds recovery to an authoritative workflow run, but a GitHub workflow run can have
multiple attempts. The final artifact name contains only `github.run_id`, and recovery downloads by
that same name plus run ID. Neither the artifact name, recovery inputs, nor validated metadata
identifies the attempt that produced the bytes.

GitHub's artifact toolkit documents the edge explicitly: reruns can create multiple artifacts with
the same name in one workflow run, and name lookup returns the latest match. The workflow-run API
also exposes `run_attempt`, and GitHub provides an attempt-addressed workflow-run endpoint. Run-level
identity is therefore insufficient when the transported object is attempt-scoped.

## Evidence

- Consolidation uploads `panel-null-measurement-${{ github.run_id }}`.
- Recovery downloads that name with `run-id: ${{ inputs.recovery_run_id }}` and no attempt input.
- `recover_panel_null.py` validates run ID, repository, workflow, event, status, and head SHA, but
  its metadata model has no `run_attempt`.
- The official `@actions/artifact` client source states that multiple same-named artifacts can
  exist because of a rerun and that lookup returns the latest one:
  `github.com/actions/toolkit/blob/main/packages/artifact/src/internal/client.ts`.
- GitHub's workflow-runs REST API exposes
  `GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}`.

## Impact

If a run is rerun, publish-only recovery can change artifact selection without changing the
requested run ID or any ADR-088 field. The chosen bytes may still be a valid, canonical
`PanelNullCalibration` with the same code SHA, so every existing check passes. For a fixed one-look
measurement, "latest artifact with this name" is not a scientific identity.

The 400-panel measurement remains unspent, so no existing artifact is affected.

## Required correction

Make the producing attempt explicit and immutable: include `github.run_attempt` in the final
artifact name, require both recovery run ID and recovery attempt, fetch the attempt-addressed
authoritative metadata, and require its `run_attempt` to match before destination mutation. The
download name must include the same pair so the artifact action never performs a latest-by-name
choice across attempts.

## Resolution

Resolved by ADR-089. The final artifact name now includes the producing run attempt; recovery
requires the matching run ID and attempt, queries GitHub's attempt-addressed run record, and rejects
metadata attempt drift before destination mutation. Partial recovery identity fails in a dedicated
workflow preflight. No workflow was dispatched and no generated data changed.
