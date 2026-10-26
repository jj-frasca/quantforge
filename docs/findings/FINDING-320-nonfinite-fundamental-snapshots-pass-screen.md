# FINDING-320: Nonfinite fundamental evidence passes screening and serializes as absence

- **Status:** Open — enabled-screen corrected by ADR-378; numeric persistence remains open
- **Date:** 2026-10-26, Codex autonomous session 3 (ISO2026-W44)
- **Severity:** Medium for malformed fundamental evidence
- **Affected:** parse_company_facts, FundamentalSnapshot and screen_fundamentals
- **Related:** ADR-017, ADR-377, FINDING-319

## Evidence

The actual parser can produce infinite growth from finite synthetic CompanyFacts:
prior revenue 1e-308, current revenue 1e308 and current net income 1e308 yield
positive infinite growth and net margin 1.0. Default fundamental screening passes;
model_dump_json serializes growth as null. Changing current revenue and net income
to -1e308 yields negative infinite growth, margin 1.0 and a failed default screen,
but also serializes growth as null. All raw numeric inputs in both cases are
finite. Externally supplied NaN growth or margin also passes its enabled check.

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

This is a partial correction. FundamentalSnapshot construction, parsing and JSON
serialization are unchanged: nonfinite evidence can still lose its numeric value
on persistence. Other snapshot fields and invalid-versus-unavailable provider
semantics remain open and require separate reviewed decisions. ADR-377 protects
validated criteria, not source metrics; unchecked copies are separate concerns.
No threshold, search, gate, accounting identity or historical record changes.

## Verification

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
