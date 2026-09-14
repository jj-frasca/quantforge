# FINDING-026: Panel-null scratch artifacts lose workflow-run attempt identity

- **Severity:** High — a full rerun can select or merge frozen inputs and complete-panel shards
  from different attempts of the same run before the fixed measurement is consolidated
- **Found:** 2026-09-14 by Codex hostile review of ADR-089 artifact provenance
- **Status:** Resolved by ADR-090
- **Affected:** `panel-null-calibration.yml`

## Finding

ADR-089 attempt-qualifies the final measurement artifact and publish-only recovery, but the normal
execution path still names its frozen input `panel-null-frozen-inputs-<run_id>` and its shards
`panel-null-shard-<index>`. A full workflow rerun keeps the same run ID while incrementing
`github.run_attempt`, so those names are reused across attempts.

GitHub's artifact toolkit states that reruns can create multiple same-named artifacts in one
workflow run and that a name lookup selects one match. The upload-artifact migration guide also
states that wildcard downloads with `merge-multiple: true` use last-writer-wins when downloaded
artifacts contain the same file path. The current consolidation wildcard can therefore see
same-named shard archives from multiple attempts and overwrite one shard JSON with another during
extraction.

## Impact

ADR-087 requires a full-job rerun before consolidation precisely because cross-attempt partial
recovery is not a valid measurement. Reusing run-only scratch names undermines that rule inside the
supposed full rerun. Mixed cohorts will often fail the model boundary, but a complete older attempt
can also be selected consistently, and extraction order is not a scientific identity. Either case
makes rerun behavior depend on artifact service ordering rather than the current attempt.

The 400-panel measurement remains unspent, so no existing result is affected.

## Required correction

Include `github.run_attempt` in the frozen-input artifact name and in every shard artifact name.
Every download must request only the current attempt-qualified name or pattern. Preserve the global
panel indices, seeds, statistic, inference, and ADR-087 rule that only a full rerun is valid before
consolidation.

## Sources

- [GitHub artifact client](https://github.com/actions/toolkit/blob/main/packages/artifact/src/internal/client.ts)
- [upload-artifact v4 migration guide](https://github.com/actions/upload-artifact/blob/main/docs/MIGRATION.md)

## Resolution

Resolved by ADR-090. The frozen-input pair, every complete-panel shard, and their corresponding
downloads now include the current `github.run_attempt`. Consolidation's wildcard can match only
shards from its own attempt. No workflow was dispatched and no generated data changed.
