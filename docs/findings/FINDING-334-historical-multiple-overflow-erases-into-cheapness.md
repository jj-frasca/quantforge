# FINDING-334: Historical multiple overflow erases into finite cheapness

- **Status:** Corrected at computed-multiple ranking consumption (ADR-398); broader input/precision limits remain
- **Date:** 2026-10-28, Codex autonomous session14 (ISO2026-W44)
- **Producing revision:** cd69d71b
- **Affected:** compute_multiples, score_valuation, compute_fundamental_record

## Evidence

Two ordinary AnnualFundamentals rows for FY2023/2024 contain finite historical
price1e200, diluted shares1e200 and revenue1e308. FY2025 has revenue1, shares1
and no historical price. At current price1e100, historical P/S multiplication
overflows before division, leaving two infinite entries. Native ranking reports
ps_percentile0, while independent Fraction arithmetic on the accepted floats
gives finite historical multiples approximately1e92, both below current1e100:
the exact strict percentile is1. With no EPS or cash-flow inputs, score_valuation
reports value1, and compute_fundamental_record accepts value_score1. All final
valuation fields are finite or genuinely absent, so ADR-373 does not refuse.

Independent research and data reviews reproduce the actual producers. This is a
constructed arithmetic witness, not economically consistent corporate evidence,
vendor incidence, an affected historical record, graduate, trading effect or
calibration measurement. The exact percentile demonstrates incorrect ordering;
it is not an instruction to recover a replacement score.

Historical P/E overflow likewise disappears behind finite ranks. Computed
historical multiples exist even when fewer than two observations are available
or the current multiple is absent. Final output validation cannot recover the
discarded observations. Scratch reproduction: /tmp/qf-w44-s14-multiples-probe.py.

## Bounded correction and limits

ADR-398 guards the present current multiple and then every selected historical
multiple inside _ranked, before its missing-current and thin-history shortcuts.
First refusal follows current P/E, selected P/E history order, current P/S,
selected P/S history order. A zero-based ordinal identifies the computed eligible
history entry, not its fiscal year or original row. Plain named ValueError
propagates; no observation is filtered, repaired or converted to missingness.

Existing P/E arithmetic/ranking still precedes P/S arithmetic; an earlier new
P/E refusal can preempt later P/S arithmetic. Other native exceptions retain
their computation sites. Quality evaluation still precedes record valuation;
valuation refusal precedes DCF/output validation and can abort sweep output.
The value provider keeps scoring outside its acquisition fallback. No recovery,
per-company skip policy or partial output is added.

Availability is explicitly reduced for invalid computed histories even when the
current multiple is absent or history is thin. Excluded rows, valid missingness,
finite native arithmetic, strict ties, counts, flags and thresholds stay intact.
Standalone percentile_rank and direct MultiplesResult construction remain
outside this boundary, as do raw invalid operands yielding finite results,
finite rounding/underflow, source-period/PIT truth and historical record repair.
No generated record, fingerprint, accounting-v14, cohort or threshold changes.

## Verification

Before source edits,58 ordinary histories at5 current prices freeze870 complete
multiple/valuation/record JSON and Python claims plus the whole multiples module
AST. The final pre-code run has52 failures and18 passing controls:46 missing
refusals,4 expected-message mismatches against existing later ADR-373 validation,
and2 wrong hunt-error assertions against a deliberate downstream sentinel. No
collection/import failures count. An earlier run used an intentional downstream
AssertionError; the sentinel became a caught ValueError before source changes so
the final run asserts the specific earlier refusal instead.

All70 new tests pass; the parent focused suite passes198 synthetic tests.
Independent research passes135 with1 live test deselected, and data passes123;
both final reviews approve. Coverage includes all current/history P/E/P/S paths,
exact accepted-operand overflow evidence, NaN/infinity, named order, absent/thin
history, excluded rows, native finite Hypothesis controls, real provider/hunt
errors with screening off/on and a fully mocked real sweep abort before output.
Parent and both reviewers replay all870 complete baseline claims and the entire
module AST outside the exact two guards/math import unchanged. Full foreground
gate and exact post-push CI receipts are recorded separately in the session ledger.
