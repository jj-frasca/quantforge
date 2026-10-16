# FINDING-254: Retention can lower a valid cumulative-trial prior

- **Date:** 2026-10-16
- **Status:** Resolved — ADR-300
- **Area:** retain_recent and PartitionedExperimentStore retention

## Reproduction

Seven distinct canonical nongraduates for one symbol have consecutive UTC dates
and lifetimes [100,4,4,4,4,4,4]. Each trial explicitly records four configurations;
every record satisfies ADR-299. The original store prior is100. Latest-five
retain_recent returns five lifetime4 records, so the retained memory-store prior
is4. Independent review reproduced the pure helper and canonical-store path.

The current test named retention_never_lowers_the_mintrl_bar uses increasing
counters, where latest and maximum coincide. It remains correct on that domain;
it does not establish the claimed general pruning invariant. ADR-066 explicitly
recognizes resets/clock skew and chooses max rather than creation order.

This is synthetic valid-record evidence. No actual false graduate, historical
production undercount or changed calibration rate is established. Quota None
also currently means an unbounded slice; this differs from migration's explicit
lossless wrapper contract and is made invalid at bounded interfaces by ADR-300.

## Current committed-pool audit

All 607 research-pool files, 3,294 rows, were read without writes. Under current
quota5 there is zero present maximum loss and every current row remains retained.
AVB, COO, EA and EQR have a nongraduate maximum above their newest nongraduate,
but that maximum is still represented by current retained records. No conclusion
about already-deleted history is possible.

Receipt: `/tmp/qf-w42-s21-retention-current-pool-audit.json`, SHA256
`394df1b8ca4ee9b323c8cd19825ef6413c11f51556b7eb142c68c8cbaccc10ab`.
All 607 source hashes unchanged; ordered source aggregate:
`8f7072f19ef9adae9ff58b47afd2d1bf64777db4feadcf1a1a9a466e362ab1e0`.
Scratch reproduction: `/tmp/qf-w42-s21-retention-max-review.md`.

## Governed correction and limits

ADR-300 retains one original maximum-count nongraduate only if graduates/latest-N
would lose the prior. Bound nongraduates by N+1 and preserve original records,
existing policy output order, stable first-witness ties and exact old output when no witness
is needed. Quota0 preserves positive prior; zero-only history may remain empty.
Validate original nonnegative integral quota before bounded-helper iteration and
store filesystem work, while preserving migration's explicit lossless None rule.

No generated file is authored, no lifetime is rewritten and no old missing count
is guessed. Max aggregation, same-UUID replacement semantics, numerical estimators,
thresholds, accounting-v14 and calibration remain. The invariant concerns canonical
records supplied to pruning, not arbitrary mutation or previously discarded history.

## Verification

Actual final preimplementation run observed 38 failing regressions and six preserved
controls in 4.29s (`/tmp/qf-w42-s23-retention-final-red.log`). The earlier receipt
records 36 failures/three preserved before adding graduate and stable-date cases.
After the narrow fix, 69 new/existing retention-store-migration tests passed,
including Hypothesis per-symbol max preservation, N+1 bounds, original object
identity, stable order, idempotence and exact prior output when no witness is
needed. Strict typing passed for 184 source files.

Independent review approved the implementation and independently reran all69 tests.
Its fresh read-only policy audit validated all607 partitions/all3294 records:
old3294/new3294, zero represented max losses, zero ordered output differences,
zero added witnesses; all original file hashes stayed unchanged. Receipt:
`/tmp/qf-w42-s23-retention-audit.json`, SHA256
`501a764061501a643b225dcd12fd6bf08844ae1f7cb07bcdc500d3f39fc975cc`.
This current-snapshot comparison cannot recover discarded historical evidence.
Parent AST scope guard separately verifies only retention and constructor quota
logic changed, plus the max-helper explanatory docstring; other aggregation,
search, gate, schema, I/O and migration executable nodes remain exact.

Foreground `make check-all PYTEST_WORKERS=8` completed green:
12,023 backend tests, 97.40% backend coverage; 381 frontend tests,
97.66% frontend statements. Backend/frontend lint, format and type checks passed.
Log: `/tmp/qf-w42-s23-check300.log`. No production source changed after the
focused green run; later changes only added verification receipts to docs.
