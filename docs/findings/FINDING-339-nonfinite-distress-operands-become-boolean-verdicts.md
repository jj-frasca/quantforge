# FINDING-339: Nonfinite distress operands become boolean verdicts

- **Date:** 2026-10-29, Codex autonomous session19 (ISO2026-W44)
- **Status:** Corrected within latest-year distress input consumption under ADR-404
- **Severity:** Medium — invalid source evidence can produce an ordinary distress verdict
- **Producing revision:** `b011b2b5`
- **Affected:** `financial_distress` and `make_distress_provider`

## Evidence

An ordinary single-row AnnualFundamentals history with assets100, equity-10,
net income-1 and operating cash flow-1 produces distressed=True. Replacing either
income or cash flow with NaN or positive infinity produces distressed=False with
no reasons. Negative infinity instead contributes to distressed=True with the
ordinary negative-income/cash-flow reasons. The provider returns the same finite
boolean payloads. A missing operand gives False by the intentional missingness
policy, but nonfinite evidence is not missing evidence.

Parent and independent research probes reproduce these synthetic cases. This
establishes invalidity erasure, not the economic truth of any invalid input.
No actual company, SEC response, source incidence, affected graduate, trade or
calibration outcome is established. The hunt CLI wires this provider, but no
provider service or real search was executed for this finding.

ADR-384 validates numeric safety outputs; ADR-385 preflights five balance-sheet
operands. Neither consumes these two profitability inputs. ADR-389 checks them
inside Piotroski scoring, which the direct distress consumer does not call.

## Bounded correction and limits

Preserve empty-history behavior and the existing financial_safety call first,
including its source and finite-derived arithmetic errors. Then require each
present latest-year net_income and operating_cash_flow finite, in that order,
before either sign comparison. Raise a plain ValueError naming the first invalid
field and financial distress. Missing peers or an otherwise impossible veto must
not hide present invalidity; availability is deliberately stricter in these cases.

Preserve None, finite native comparisons, reasons and their order, older rows,
unrelated fields and global Annual/history schemas. Consumer evaluation stays
outside the provider's acquisition-error catch, so refusal propagates rather
than becoming unscored None. Existing hunt error handling remains unchanged.
No fallback, skip, recovery, threshold, accounting-v14, historical/generated
record or frozen-cohort change is authorized. Finite ratio precision, economic
denominator domains and source-period/PIT truth remain separate limitations.

## Verification

Before implementation, 865 complete direct/provider/empty results, the whole
distress-module AST and the original test-file SHA256 were frozen. The corpus
covers finite or absent consumed operands and ignored older-row NaN evidence.
The actual pre-code run has 48 missing-refusal failures and 16 passing controls,
with no harness failures and no production diff. All 64 new tests then pass;
the parent focused suite passes 441 synthetic tests. Independent research review
approves all six paths, verifies the same RED receipt, passes the same 441 tests
and replays all 865 results, the whole scoped AST and the original test SHA exactly.
The guard adds only a math import and seven lines after safety evaluation.
Foreground full-gate and exact publication CI receipts are retained in the
session ledger; no historical record is rewritten.
