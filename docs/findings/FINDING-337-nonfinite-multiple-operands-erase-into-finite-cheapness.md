# FINDING-337: Nonfinite multiple operands erase into finite cheapness

- **Status:** Corrected at reached multiple-operand consumption by ADR-401; broader source/precision limits remain
- **Date:** 2026-10-29, Codex autonomous session16 (ISO2026-W44)
- **Producing revision:** ca6d8573
- **Related:** FINDING-334; ADR-022/023/373/398

## Evidence

Ordinary FundamentalsHistory.model_validate accepts three annual rows with
EPS=+inf. Using the existing three-year multiples fixture at current price55,
compute_multiples reports finite P/E0, percentile0 and history count3;
score_valuation reports finite value2/3. Nonfinite earnings become a maximum
cheapness component. ADR-398 checks computed multiples and ADR-373 checks final
output; both see finite evidence here. Independent research/data reviews reproduce
the actual pure scorers. Scratch reproduction and written pre-adoption review:
/tmp/qf-w44-s16-source-operands-probe.py and source-operands-finding.md.

This is a constructed malformed-input validity defect, not a valid-input formula
error or measured vendor occurrence, historical record, graduate, trading effect
or calibration result. Invalid operands have no correct replacement valuation.
F334 explicitly left raw invalid operands yielding finite results outside its
computed-result correction. No historical repair or source/PIT claim follows.

## Bounded correction

ADR-401 checks operands only when the existing expression reaches their first
numeric comparison or arithmetic use, returning the original finite operand.
NaN and either infinity refuse with named plain ValueError. Missingness tests
alone do not consume a numeric operand. Existing short circuits leave dormant
fields untouched, including historical EPS behind absent/nonpositive prices and
current shares behind nonpositive revenue. P/E still completes before P/S;
current P/S consumes revenue, then current price, then shares. Historical traversal
and comparison order stay. Labels name stage/field, without claiming row identity.

The correction includes eligibility comparisons: malformed NaN/-inf may no
longer silently remove a numerically inspected observation. This explicit
availability restriction adds no filtering, recovery or missingness fallback.
Finite negative/zero values retain existing eligibility, including nonpositive
current shares. Native formulas, ranks, ties, counts, flags and thresholds stay.
Computed-result guards remain necessary for overflow of finite operands.

Provider scoring remains outside acquisition fallback; hunt errors remain per
symbol. Record quality still runs before valuation and sweep refusal may abort
output. Shared schemas, direct result construction and percentile_rank are
unchanged. Dormant and unrelated source fields are not certified. The evidence
concerns ordinary validated floats, without a new unchecked scalar-protocol
policy, full source validation, period/PIT authentication or precision recovery.
No generated record, fingerprint, v14 or frozen cohort changes.

## Verification

Before source edits, 58 histories at 5 prices froze 870 complete multiple,
valuation and fundamental-record JSON/Python claims, the multiples schema and
whole module AST. The actual precode run produced 39 failures and 32 controls:
24 missing refusals and 15 expected-message mismatches against later existing
computed-result refusals. No collection/import failure is counted. There are
68 new cases/property tests plus 3 retained assertions updated for earlier
source-operand refusals. The existing computed-overflow regressions remain.

The parent focused suite passed 274 synthetic tests with 1 live test deselected;
both independent final reviews approved with 280 passing and 1 live test
deselected each. An initial focused command referenced a nonexistent test path
and ran zero tests; it is excluded from evidence. Checks cover ordinary validated
infinite EPS, all reached operands, dormant branches, co-invalid error precedence,
real injected provider/hunt refusal and native finite Hypothesis rank invariants.
Parent and both reviewers replayed all 870 complete claims and the schema
exactly; stripping only the exact helper and ten wrappers recovers the original
whole-module AST. No numeric replacement or valid-input precision claim follows.

Foreground full-gate and exact publication CI receipts are recorded separately
in the session ledger. This evidence establishes the bounded malformed-operand
correction, without source authentication, historical reconstruction or incidence
claims.
