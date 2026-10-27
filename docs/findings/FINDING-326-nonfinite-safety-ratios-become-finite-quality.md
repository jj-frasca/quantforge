# FINDING-326: Nonfinite safety ratios become finite quality

- **Status:** Corrected at ordinary numeric SafetyScore construction (ADR-384); full local verification passed, upstream limits remain
- **Date:** 2026-10-27
- **Affected:** fundamentals/quality.py SafetyScore and its quality/distress consumers
- **Producing revision:** f30b7127 (before ADR-384)

## Evidence

A synthetic ordinary AnnualFundamentals FY2025 row with revenue100,
total_current_assets=NaN and total_current_liabilities=100, other line items
absent, constructs inside FundamentalsHistory. financial_safety returns
current_ratio=NaN. quality_score clips that ratio through min/max; NaN takes the
upper bound, contributing safety1. With the single-year F-score0 and missing gross
profitability, quality_score returns finite0.5. compute_fundamental_record accepts
quality_score0.5, f_score0, gross_profitabilityNone. The safety ratio serializes as
null even though it contributed a maximal component. The corresponding missing
current-assets control has no available safety component and quality0.

Both independent data and research reviews reproduced the issue; research also
used the actual parser on synthetic accepted CompanyFacts-shaped input. This is
not evidence that SEC published a nonfinite fact. No actual company, generated
record, search, graduate, trading effect or calibration outcome is established.
Finite-source extreme ratios can also overflow into infinity. Infinite ratios
may saturate to the same finite clipping bound as their exact-real counterpart;
they still represent nonfinite component evidence rather than measured ratios.

## Bounded correction

ADR-384 requires finite non-null leverage_ratio/current_ratio at ordinary
SafetyScore construction and JSON validation, including financial_safety returns.
ValidationError propagates before quality clipping and distress comparison.
An otherwise distressed synthetic history with a NaN liquidity ratio currently
still vetoes via its finite insolvency leg. Refusal must propagate after the
history lookup rather than turn that veto into availability fallback None.
The existing make_distress_provider catches acquisition errors only, leaving
consumer validation outside its try. No wrapper change or None recovery is needed.

This does not validate AnnualFundamentals globally, recover arithmetic, enforce
ratio ranges, change finite formulas/thresholds, or repair historical records.
Retained-earnings NaN can already become a boolean False before SafetyScore;
nonfinite input denominators may yield finite ratios. Those upstream cases and
unchecked model copies remain outside the numeric construction boundary.
A sweep scoring refusal can fail the whole shard; no partial-success catch is added.

## Verification

Before source changes, 324 complete ordinary history/quality/distress/record
claims, 14 finite/nullable/coercible SafetyScore constructor/JSON controls and the
whole quality-module AST were captured at /tmp/qf-w44-s7-safety-baseline.{py,json}.
Actual pre-code evidence contains 32 expected missing-validation failures and 21
passing controls. The raw log reports 33 failures because one synthetic parser
fixture omitted its accession key and raised KeyError; that harness failure is
excluded from TDD evidence. The fixture was corrected after the patch, and its
passing parser/consumer assertion is additional postpatch coverage. Initial GREEN
had 53 passes and that fixture error; the corrected 54-test suite passes.

The patch adds only SafetyScore's finite ConfigDict keyword. The parent focused
suite passes 121 synthetic tests; independent data review passes the same 121 and
research review passes 66. Both approve the source/tests and reproduce all 324
complete claims, 14 constructor/JSON controls and the whole quality-module AST
except the single keyword exactly. The original RED log and final review receipts
are /tmp/qf-w44-s7-safety-red.log and /tmp/qf-w44-s7-adr384-*.md. Foreground make check-all passed: 15,434 backend and 746 frontend tests,
97.43%/97.88% coverage, lint/format and strict types. Exact post-push CI is
verified by the local session ledger after publication. No historical record is rewritten.
