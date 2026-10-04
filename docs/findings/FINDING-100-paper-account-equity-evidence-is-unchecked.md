# FINDING-100: Paper-account equity evidence is unchecked

- **Date:** 2026-10-04
- **Severity:** High — malformed observations can reach the durable paper-account ledger
- **Status:** Resolved by ADR-169

## Evidence

`EquityPoint` accepts nonfinite floats, naive timestamps, negative position counts, and only one
member of its nullable benchmark/alpha pair. Explicit validation trusts unchecked point copies.
`JsonFileEquityCurve.save` creates directories and serializes incoming copies without reconstruction,
including JSON NaN/infinity. Neither the store nor append enforces chronological snapshot identity.
Append divides by unchecked nominal and inception denominators.

Direct-model, append, and writer TDD regressions reproduce these gaps. Writer tests assert an invalid
batch cannot replace existing bytes or create a destination directory.

## Independent historical arithmetic audit

The 46 committed observations were inspected read-only. All 46 nominal returns equal
`equity / 100000 - 1`. Among the 33 measured benchmark rows, 26 alphas equal the historical nominal
return minus benchmark and seven equal the ADR-141 observed-inception return minus benchmark.
Thirteen rows have neither benchmark nor alpha. No row is unexplained; timestamps strictly increase.
The historical formula difference is intentional evidence under ADR-141, not a new finding.

## Impact and limits

The defect is an unvalidated write/arithmetic boundary, not evidence the committed curve is corrupt.
Real account cash can be negative and observed equity can be zero/negative; rejecting those observed
balances would hide genuine insolvency. Positive denominators are required only for meaningful
return measurement. Stored point scalars cannot be universally rebound to a nominal $100k baseline
because append supports an explicit custom starting equity and historical alpha semantics differ.

## Correction

ADR-169 validates intrinsic points and ordered batches, revalidates unchecked copies before all
writer side effects, and validates append denominators. No generated data is changed or historical
formula restated; no broker is contacted.
