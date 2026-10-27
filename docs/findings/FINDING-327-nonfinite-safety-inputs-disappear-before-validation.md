# FINDING-327: Nonfinite safety inputs disappear before validation

- **Status:** Corrected within latest-year safety input consumption (ADR-385); full local verification passed
- **Date:** 2026-10-27
- **Producing revision:** 93c62741, after ADR-384
- **Affected:** financial_safety latest-year input consumption

## Evidence

ADR-384 correctly refuses nonfinite numeric SafetyScore outputs. It cannot detect
invalid input that already became finite or boolean output. Ordinary annual history
with revenue100, retained_earningsNaN and other optional values absent yields
negative_retained_earningsFalse, a maximal retained-earnings safety contribution,
quality0.5 and an accepted FundamentalRecord. Finite current assets100 divided by
infinite current liabilities yields finite current_ratio0 and accepted quality0;
not all erased invalidity inflates a score. Both independent reviewers reproduced
these cases on the ADR-384 source. No actual vendor/company, search, graduate,
trading effect or historical generated-record incidence is established.

Missing peers and zero denominators erase additional invalidity: NaN equity with
missing or zero assets, infinite assets with missing equity, NaN current assets
with zero liabilities, and NaN liabilities with missing current assets. The old
ratios can be absent even though a present source operand is invalid. A finite
insolvency veto with NaN retained earnings currently still vetoes. Refusal must
remain an explicit consumer error after lookup, never availability fallback None.

## Correction and limits

ADR-385 preflights exactly five latest-row operands before safety arithmetic or
comparisons: total_assets, total_equity, total_current_assets,
total_current_liabilities, retained_earnings. Each present value must be finite;
None remains valid but does not excuse a different invalid operand. Plain ValueError
names the first invalid field. This intentionally precedes missing/zero shortcuts
and can precede ADR-384 ValidationError. Finite-source overflow still reaches
ADR-384; it is not recovered. Native finite math, ranges and thresholds stay.

The guard does not validate older years or Annual/history globally, nor revenue,
net income, operating cash flow, F-score, gross profitability or other scorers.
It does not certify PIT/period selection, economically meaningful ratios, exact
arithmetic, source truth or unchecked-instance provenance. Sweep scoring may fail
its shard before output; no new skip, recovery or partial-output policy is added.
Historical lost input evidence is not reconstructed.

## Verification

Before source changes the parent captured 324 complete ordinary history/quality/
distress/record claims, 14 constructor/JSON controls and whole quality-module AST
at /tmp/qf-w44-s7-safety-operands-baseline.{py,json}. Independent prospective
reviews approve the explicit availability/precedence policy. Actual pre-code RED
contains 84 expected failures and 75 passing controls: 81 missing ValueError
refusals and three intentional input-field error-precedence assertions. No
collection/import/harness failures are counted. The 105 new tests and updated
ADR-384 consumer assertions pass with 226 focused tests total. Direct SafetyScore
constructor/JSON refusals remain, and two explicit finite-input-overflow cases
still require downstream ValidationError.

Parent replay reproduces all 324 complete claims, 14 constructor/JSON controls
and the whole quality-module AST except the exact five-field loop/math import.
Final data review passes 226 tests and research review passes 171; both approve
all eight paths and independently reproduce the baseline/AST. Foreground
make check-all passes 15,539 backend and 746 frontend tests, 97.43%/97.88%
coverage, lint/format and strict types. Exact CI is recorded in the session ledger
after publication. No generated evidence is rewritten.
