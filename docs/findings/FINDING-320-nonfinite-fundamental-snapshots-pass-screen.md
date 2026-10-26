# FINDING-320: Nonfinite fundamental evidence passes screening and serializes as absence

- **Status:** Prospectively corrected (ADR-378/379); historical numeric loss is unrecoverable
- **Date:** 2026-10-26, Codex autonomous session 3 (ISO2026-W44)
- **Severity:** Medium for malformed fundamental evidence
- **Affected:** parse_company_facts, FundamentalSnapshot and screen_fundamentals
- **Related:** ADR-017, ADR-377, FINDING-319

## Evidence

Before ADR-378, the actual parser could produce infinite growth from finite synthetic CompanyFacts:
prior revenue 1e-308, current revenue 1e308 and current net income 1e308 yielded
positive infinite growth and net margin 1.0. Default fundamental screening passed;
model_dump_json serialized growth as null. Changing current revenue and net income
to -1e308 yielded negative infinite growth, margin 1.0 and a failed default screen,
but also serialized growth as null. All raw numeric inputs in both cases were
finite. Externally supplied NaN growth or margin also passed its enabled check.

ADR-378 closed that enabled-screen admission. Snapshot construction still accepted
nonfinite values and serialization loss persisted until ADR-379's correction.

Parent pure-parser receipts and independent research/data probes confirmed the
cases. No provider, network, search, calibration or generated-data write occurred.
No actual affected production row or false graduate is established. Separately,
482 stored default screens from the latest 598 discovery rows replayed exactly;
116 rows had absent fundamentals and absent screens. This bounded metadata replay
cannot certify original source truth, missingness causes or point-in-time validity.

## Why a snapshot-only constructor guard is insufficient

Pydantic finite-only snapshot validation raises ValidationError, a ValueError
subclass. The daily shard's fundamentals_provider catches ValueError and returns
None. The unmodified search skips fundamental screening for absent fundamentals,
and its fundamental veto permits a missing screen, conditional on other gates.
A constructor-only fix could therefore turn the negative-overflow witness's
existing fundamental veto into eligibility. This is a counterfactual constructor
probe and source-control-flow inference, not execution of a modified search.

## Correction and remaining scope

ADR-378 adds an explicit failed-screen reason for a nonfinite metric only when
its corresponding criterion is enabled, after the existing None branch and
before the native comparison. It introduces no exception that the provider can
convert to missingness. Negative infinity remains vetoed; positive infinity and
NaN become vetoed. Finite comparisons and missing-value reasons remain unchanged.
A disabled criterion continues to ignore its metric, including nonfinite values.

ADR-378 was a partial correction: snapshot construction and persistence stayed
unchanged. ADR-379 now specifies finite values for all six canonical numeric
fields together with ValidationError propagation in all three hunt wrappers.
Existing nested Experiment/store revalidation acquires that refusal too, so an
invalid copied claim cannot reach those writers. All ValidationErrors propagate,
including malformed nonnumeric fields already rejected by the old model. Plain
ValueError/OSError fallbacks, raw parser error classification, history models and
custom-provider behavior retain their separate semantics.

Historical values already lost to null remain irrecoverable. Ordinary validated
snapshots and existing experiment writers are covered; standalone unchecked copies
can still serialize invalid evidence without revalidation. No universal source
validity or invalid/unavailable classification is claimed. ADR-377 protects
criteria and ADR-378 retains its enabled-screen defenses. No threshold, search,
gate, accounting identity or historical record changes.

## ADR-378 verification

Before implementation, 19 tests failed for the nonfinite admission/reason gaps
and 17 controls passed. After adding the two guards, all 36 new tests passed,
including both finite-input parser overflow directions and a Hypothesis invariant
that no finite enabled minimum admits a nonfinite metric. Disabled checks, None
reasons and simultaneous enabled/disabled geometry are covered.

The parent focused suite passed 101 tests; an additional search-orchestrator suite
passed 83. Independent research/data runs passed 101/49 tests and both reproduced
the exact prepatch replay of 486 complete finite/None screen claims. The complete
module AST matches after removing only the two guards, math import and targeted
docstring difference. Both final reviews approved the qualified correction.

Foreground make check-all passed 15,086 backend tests (97.43% coverage), 746
frontend tests (97.88%) and all lint/format/type gates. Logs:
/tmp/qf-w44-s3-screen-red-final.log, /tmp/qf-w44-s3-screen-green.log,
/tmp/qf-w44-s3-screen-search-green.log and /tmp/qf-w44-s3-check378.log.
Parent source receipt: /tmp/qf-w44-s3-snapshot-audit.json; latest stored-screen
replay: /tmp/qf-w44-s3-fundamental-replay.json. No generated file was authored.

## ADR-379 verification

Before source edits, 113 meaningful failures and 55 passing controls established
the missing constructor/provider/nested-writer refusal. The raw log reported 119
failures; six nested-JSON tests instead failed on a UUID serialization mistake and
are excluded from preimplementation evidence. Those six harness cases were fixed
and passed as postimplementation JSON regression coverage.

The final parent focused suite passed 264 tests, including all six numeric fields,
all three actual CLI provider closures, both parser-overflow directions, unchanged
availability fallbacks, per-symbol errors before search and three stores refusing
invalid nested copies before mutation. Hypothesis verifies exact finite snapshot
JSON round trips. The retained ADR-378 tests use explicit unchecked numeric copies;
its parser-overflow cases now require constructor refusal before screening.

Independent research/data runs passed 264/207 tests. Both reproduced exact replay
of all four source-module ASTs (excluding only the agreed keyword/import/catches),
2,688 canonical snapshot JSON values, 3,301 rows and 607 file hashes. Research review
corrected the finding timeline before publication. Historical lost nulls remain
unidentifiable; this inventory does not validate original vendor truth.

Foreground make check-all passed 15,224 backend tests (97.43% coverage), 746
frontend tests (97.88%) and all lint/format/type gates. Logs:
/tmp/qf-w44-s3-snapshot-red-final.log, /tmp/qf-w44-s3-snapshot-green-final.log and
/tmp/qf-w44-s3-check379.log; replay helper /tmp/qf-w44-s3-snapshot-baseline.py.
No generated records, thresholds or calibration cohorts were authored.
