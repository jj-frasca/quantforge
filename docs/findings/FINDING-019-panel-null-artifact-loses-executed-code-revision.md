# FINDING-019: Panel-null artifact loses the executed code revision

- **Severity:** High — a completed methodology artifact can be attributed to code that did not
  produce it
- **Found:** 2026-09-11 by Codex hostile review of ADR-081 workflow orchestration
- **Status:** Resolved by ADR-083
- **Affected:** `panel-null-calibration.yml`, `PanelNullCohort`, panel preparation/batch commands

## Finding

ADR-081 freezes the source bytes, cohort, search fingerprint, gate fingerprint, generator version,
and diagnostic version, but it does not record the git revision whose code executes the 400 panel
replicates. A workflow dispatch pins every job to its triggering `github.sha`; after a long run,
the consolidation job rebases its generated-data commit onto the then-current `master`. The file
therefore appears beside newer code while carrying no field that identifies the older code that
actually produced it.

Search and gate fingerprints are configuration identities, not implementation identities. A fix to
backtesting, walk-forward, purged CV, source reconstruction, or panel inference can change measured
values without changing either fingerprint. The existing generator/diagnostic labels are manually
maintained method names and likewise do not identify the complete executable tree.

## Evidence

- `PanelNullCohort` has no git revision or equivalent immutable code identity.
- The workflow checks out the dispatch revision in every job, but neither preparation nor batch
  receives `${{ github.sha }}`.
- Consolidation commits the artifact and then runs `git pull --rebase origin master`, so the
  generated commit's eventual parent is not reliable evidence of the revision used by the jobs.
- `calibration_search_version` hashes resolved strategy/grid/gate policy, not implementation bytes.

## Impact

A future code-only correction can leave the stored fingerprints unchanged. The completed artifact
could then be read as evidence for the corrected implementation even though every replicate ran the
pre-correction code. This is a reproducibility and methodology-attribution defect; it does not alter
an existing result because the ADR-081 measurement has not been dispatched.

## Required correction

Record one explicit 40-character lowercase git revision in the frozen cohort manifest, pass the
dispatch `${{ github.sha }}` into preparation and every batch, and fail before search execution when
the batch's declared revision differs from the manifest. The consolidated artifact then preserves
the executed revision even if its commit is rebased onto newer master.

## Resolution

ADR-083 implemented the required correction. `PanelNullCohort.code_revision` requires an exact
40-character lowercase git SHA; the preparation and batch commands require it; and
`panel-null-calibration.yml` passes the workflow's `GITHUB_SHA` to both stages. The production batch
loads and revalidates the frozen cohort/source pair, then rejects revision drift before constructing
the search. Shards and consolidated calibration artifacts retain the exact cohort identity, while
the recovery path additionally requires the authoritative source run's `head_sha` to match it.

Regression coverage includes schema rejection of malformed revisions and a batch test proving a
mismatched revision fails before the search callback can execute. No panel-null measurement has
been dispatched and no generated artifact was changed by closing this finding.
