# ADR-090: Bind panel-null scratch artifacts to one workflow-run attempt

- **Status:** Accepted
- **Date:** 2026-09-14
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Acts on:** FINDING-026
- **Extends:** ADR-081, ADR-087, ADR-089

## Context

ADR-087 permits a full workflow rerun before consolidation and forbids mixing partial work across
attempts. ADR-089 identifies the final measurement and recovery request by `(run_id, run_attempt)`,
but the normal path's frozen-input and shard artifacts still use names that omit the attempt.

GitHub retains one run ID across reruns. Its artifact client explicitly allows duplicate names
created by rerun attempts, and wildcard merge extraction is last-writer-wins for colliding paths.
Run-only scratch names therefore do not prove that consolidation consumed one complete attempt.

## Options considered

1. **Trust current-run artifact lookup.** Rejected: a workflow run contains multiple attempts, and
   GitHub documents duplicate-name selection across reruns.
2. **Rely on cohort validation after download.** Rejected: validation can detect many mixtures but
   cannot make ambiguous service selection a valid provenance rule or prove the current attempt won.
3. **Attempt-qualify every scratch artifact and download.** Chosen: the workflow context already
   supplies an immutable positive attempt number and no model or statistic needs to change.

## Decision

Name the immutable input pair
`panel-null-frozen-inputs-<run_id>-<run_attempt>`. Name each complete-panel shard
`panel-null-shard-<run_id>-<run_attempt>-<shard_index>`. Batch jobs download the exact current
input-pair name; consolidation downloads only the current attempt-qualified shard pattern.

The existing cohort/source validation, complete 0–399 index requirement, and fixed inference remain
unchanged. This decision does not permit failed-job reruns: ADR-087 still requires rerunning all
jobs before consolidation.

## Consequences

- A full rerun cannot resolve scratch artifacts from an earlier attempt by name.
- Wildcard consolidation cannot merge colliding shard paths across attempts.
- Artifact UI names become longer but state the complete production identity.
- No seed, panel, statistic, threshold, generated artifact, or measurement changes.

## Reversal

Remove the attempt suffixes from scratch names and downloads. That restores FINDING-026 and is
unsafe once any workflow run has more than one attempt.
