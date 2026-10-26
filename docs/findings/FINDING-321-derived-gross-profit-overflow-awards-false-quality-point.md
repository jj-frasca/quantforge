# FINDING-321: Derived gross-profit overflow awards a false finite quality point

- **Status:** Corrected for parser-derived gross profit (ADR-380)
- **Date:** 2026-10-26, Codex autonomous session 3 (ISO2026-W44)
- **Severity:** Medium for extreme accepted-domain fundamental arithmetic
- **Affected:** parse_company_facts_history COGS fallback; downstream quality records
- **Related:** ADR-029, ADR-117, ADR-155; distinct from FINDING-316/320

## Evidence

Before ADR-380, two adjacent synthetic years had (revenue, COGS) of (1, -2) and
(1e308, -1e308). Every raw numeric value is finite. Without a direct GrossProfit
fact, the actual history parser computed gross profit 3 then positive infinity.
Exact Fraction.from_float arithmetic on the original raw floats gives gross
margins 3 then 2: the improving-margin signal was false. Piotroski instead compared
infinity with 3 and awarded that point, producing F-score 1 rather than 0.

With the other inputs absent, quality_score and compute_fundamental_record returned
and accepted finite quality 1/9 rather than 0. Absent assets made the record's gross
profitability None, so its finite-output guard never saw the infinite gross
profit. No valuation was invoked. This differs from F316's nonfinite valuation
output and F320's snapshot/screen boundaries: the wrong durable score is finite.
Parent and independent data/research probes confirmed raw-float exact margins,
actual parser/scorer outputs and accepted record JSON, with unchanged source hashes.

The extreme scale and negative COGS are accepted-domain synthetic inputs, not a
claim about economic plausibility. No affected production row, hunt admission,
false graduate, trading effect or statistical calibration outcome is established.

## Correction and limits

ADR-380 refuses a nonfinite result immediately after the parser's fallback
revenue-minus-COGS operation with OverflowError. Direct GrossProfit precedence and
every finite native subtraction result remain. This is explicit numerical refusal,
not missingness, zero substitution or numerical recovery. Existing history
providers propagate OverflowError instead of converting it to unavailable data;
the universe already handles it as a per-symbol arithmetic error before search.

The fundamental sweep explicitly counts/skips acquisition-time OverflowError and
continues to later companies without scoring the invalid history. That also
classifies preexisting huge-integer float-conversion overflows as skipped rows;
unrelated arithmetic exceptions retain their previous behavior. Existing generated
pool retention remains unchanged and may retain an earlier row for a failed update.

This bounded correction does not validate all AnnualFundamentals/history inputs,
direct nonfinite GrossProfit facts, free-cash-flow arithmetic or arbitrary scorer
ratios. Finite results preserve native rounding; exact-real subtraction and general
financial-score correctness are not claimed. No threshold, estimator, gate, search,
accounting identity, generated record or frozen cohort changes.

## Verification

Before source changes, 14 tests failed and 15 controls passed, including explicit
Hypothesis overflow examples. The implementation then passed 98 focused tests.
The property uses exact Fraction subtraction on original raw floats: accepted
results preserve native finite subtraction bit for bit; refusal requires a
nonfinite native result and an exact magnitude beyond binary64's finite range.
It does not claim exact subtraction for rounded finite results.

Both independent research/data runs passed all 98 focused tests and exactly
replayed 34 complete finite/direct/signed-zero parser, F-score, quality and record
claims plus both module ASTs after stripping only the agreed guard/docstring/catch.
Tests exercise actual injected EDGAR history providers, universe refusal before
search, actual sweep continuation from bad to good companies, raw-conversion
overflow recovery and unchanged unrelated arithmetic propagation.

Foreground make check-all passed 15,253 backend tests (97.43% coverage), 746
frontend tests (97.88%) and all lint/format/type gates. Logs:
/tmp/qf-w44-s3-gp-red-final.log, /tmp/qf-w44-s3-gp-green.log and
/tmp/qf-w44-s3-check380.log. No generated records or frozen cohorts changed.
Historical evidence at c080e0d5: /tmp/qf-w44-s3-annual-gp-finding-probe.{py,json,md}.
Its --compare requires the recorded prepatch behavior and source hashes and will
fail against the adopted correction. Preserve those receipts without rewriting.
Current finite compatibility uses /tmp/qf-w44-s3-gp-baseline.py --compare.
