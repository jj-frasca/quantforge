# FINDING-029: Panel-null artifacts do not validate the derived panel identity

- **Severity:** Medium — scratch and final artifacts accept an invented per-panel identity even
  though the execution contract presents that field as derived from the frozen cohort and index
- **Found:** 2026-09-21 by Codex hostile review of the unspent ADR-081 consolidation boundary
- **Status:** Resolved by ADR-097
- **Affected:** panel-null replicate execution, shard loading, direct calibration construction

## Finding

`run_panel_null_replicate` derives `panel_id` as the SHA-256 digest of the complete serialized
cohort identity plus the global panel index. Consolidation re-derives the seed and checks panel IDs
for duplicates, but never re-derives the expected ID. Consequently a JSON shard or final artifact
with an arbitrary unique `panel_id` passes validation when its cohort, index, seed, counts, and
statistics otherwise parse.

This does not by itself alter the numeric tail statistic, because the global index and derived seed
are checked separately. It does break the promised identity boundary and permits an artifact to
claim a panel label that execution could never have emitted. That weakens auditability precisely at
the untrusted persisted-artifact boundary.

## Required correction

Define one deterministic panel-identity function over the validated frozen cohort and global index.
Use it both when emitting a replicate and when validating every shard or direct final artifact.
Reject an out-of-range index before deriving an identity, and keep all seeds, generated panels,
diagnostics, inference rules, and validation thresholds unchanged.

## Resolution

Resolved by ADR-097. Execution and artifact validation now share the same derived panel-identity
function, so an arbitrary or cohort-misbound `panel_id` fails before consolidation or inference.
