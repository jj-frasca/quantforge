# ADR-088: Bind panel-null recovery to its source workflow run

- **Status:** Accepted
- **Date:** 2026-09-13
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Acts on:** FINDING-024
- **Extends:** ADR-083, ADR-087

## Context

ADR-083 records the workflow-dispatch git revision inside the panel-null cohort. ADR-087 validates
and republishes a completed artifact by source run ID without repeating the measurement. The
artifact is internally complete, but its revision is still self-asserted: recovery does not compare
it with GitHub's authoritative metadata for the selected run.

GitHub's workflow-run REST response provides the run ID, workflow path, event, completion state,
head SHA, and repository identity. These fields can bind the downloaded bytes to the intended
execution without another search, inference calculation, or generated-data mutation in a local
session.

## Options considered

1. **Trust the run-scoped artifact name.**
   - Pro: no additional API request.
   - Con: naming uniqueness is a repository convention and does not authenticate the payload's
     embedded code revision or workflow origin.
2. **Check only `head_sha == cohort.code_revision`.**
   - Pro: binds the most important methodology identity.
   - Con: another workflow at the same commit could still supply the named payload.
3. **Validate the complete source-run identity at the recovery boundary.**
   - Pro: binds repository, run ID, workflow, event, completion state, and code revision through one
     testable fail-closed check.
   - Con: recovery depends on one read-only Actions API request in addition to artifact download.

## Decision

Choose option 3. In recovery mode, query
`GET /repos/$GITHUB_REPOSITORY/actions/runs/$RECOVERY_RUN_ID` with the workflow's existing
Actions-read token and save the JSON response to scratch storage. Pass that response, the expected
repository, and the requested numeric run ID into `recover_panel_null.py`.

Before creating a parent directory or temporary destination, the recovery command requires:

- metadata `id` equals the requested run ID;
- `repository.full_name` equals the current `$GITHUB_REPOSITORY`;
- `path` identifies `.github/workflows/panel-null-calibration.yml` (allowing GitHub's appended ref);
- `event == "workflow_dispatch"`;
- `status == "completed"`; and
- metadata `head_sha` equals the validated calibration's `cohort.code_revision`.

The existing canonical-byte and complete-calibration checks remain unchanged. A source run may
conclude either success or failure because the intended recovery case is a failure after final
artifact upload; completion, not conclusion, is the required state. No artifact is downloaded from
another repository.

## Consequences

- The published artifact's executed revision becomes a fact checked against GitHub's run record,
  not a self-reported payload field.
- An artifact from another workflow, repository, run ID, event, or incomplete run fails before the
  sole-writer destination is touched.
- Recovery gains one read-only API request and no compute-heavy work.
- The panel-null measurement remains unspent; no seed, statistic, inference input, validation
  threshold, or generated artifact changes.

## Reversal

Remove the source-run metadata request and validation inputs. That restores FINDING-024 and must
not be done after recovery has ever been used to publish the fixed measurement.
