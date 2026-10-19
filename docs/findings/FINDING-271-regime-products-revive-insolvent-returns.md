# FINDING-271: Regime products revive insolvent matched returns

- **Status:** Resolved by ADR-320
- **Date:** 2026-10-18
- **Scope:** Compounded-return claim in public analyze_regimes

## Reproduction

With flat positive ordered market prices, nonnegative horizon1 and matched
strategy returns[-3,-3], the helper publishes bull total_return3 and Sharpe0.
Unit wealth passes through-2 before finishing4. RegimeBreakdownEntry accepts
the finite +300% claim. The separate[-2,-3] witness publishes total_return1
(+100%) and a finite negative Sharpe, likewise accepted by the report entry.
An aggregate wealth check cannot recover the intermediate insolvency.
Exact-1 and values below it also reach the old public helper without refusal.

Parent receipt `/tmp/qf-w42-s33-regime-wealth-parent-probe.json`; independent
review `/tmp/qf-w42-s33-regime-wealth-review.md`. Both reproduce actual helper
and report-entry behavior, without mocking the estimator or running any
strategy search, source cohort, vendor or calibration.

## Impact and correction boundary

Normal BacktestEngine already checks positive finite equity under ADR-110/177;
no affected production report, API exploit, calibration or false graduate is
established. Regime metrics remain retrospective descriptive partitions, not
an executable switching account. Their stated compounding convention still
cannot treat two negative gross factors as ordinary positive wealth.

ADR-320 adds only a native matched-return <=-1 refusal immediately after
alignment and before market calculations, grouping, products or Sharpe.
Original count/calendar checks retain their precedence. Unsafe original rows
outside the matched intersection remain outside this guard; empty and disjoint
inputs retain their existing results. No Float64 coercion, clamp, liquidation
policy, new return model, threshold, search identity, v14 or generated-data
change. Solvent scoring keeps every numerical statement. Dtype/completeness,
market-price evidence, nonfinite product recovery and aggregate projection
remain separate limitations.

## Verification

Twenty-four valid pre-edit payloads are frozen at
`/tmp/qf-w42-s33-regime-wealth-baseline.json`, SHA256
`0259b1b618af42b63cb579e9c1d82fe32f574d887b2e4f98723b25115ca47c0a`.
They include ordinary paths, zero/positive horizons, empty/disjoint, unmatched
unsafe rows, zeros, solvent losses and the native value immediately above-1.
Original source SHA256:
`3ead68e99542d824045790a4edc9012f6499faa8383a346d04bd449c61371a87`.
Independent precode scope approved. Actual preimplementation RED observed18
failures and8 preserved controls in9.33s, with production diff empty
(`/tmp/qf-w42-s33-regime-wealth-red.log`). After the guard, all26 new cases
plus65 prior regime/calendar/horizon cases passed (parent4.17s,
independent4.45s). Tests cover real revival/bankruptcy, first/interior/last
matched loss, refusal before market calculations, unmatched unsafe rows,
empty/disjoint inputs, native float64/longdouble values immediately around-1,
source nonmutation, count/calendar precedence and unchanged NumPy error policy.
Hypothesis verifies matched unsafe refusal and nonpositive solvent-path returns.
Ruff, formatting and mypy186 passed.

Parent and independent audits preserved every field of all24 valid frozen
payloads and the entire prior module AST after removing only the native guard
and restoring its docstring. All earlier guards, alignment and numerical
statements remain exact. Parent receipt
`/tmp/qf-w42-s33-wealth-parent-audit.json`, SHA256
`7e574b37673129ea143a460fa5db48a59b7bfc85f2cc9e2275913a22539645f8`.
Independent receipt `/tmp/qf-w42-s33-regime-wealth-final-audit.json`, SHA256
`41c35986645ec76547ef117c0597bef6fd2d4ac32c52832f4700fe29aefffeba`.
Final source SHA256:
`020f7506867f89021a528f40b6fcc3879af4eb210f85ba5fadde03904f5eda34`.
Prior tests, helper, frontend and generated data retain their bytes.
Independent final five-path research review approved. W43 session1 resumed the
five inherited paths without changing source: fresh independent review again
approved, with91 focused tests passing in4.59s and all24 frozen payloads plus
the complete prior AST preserved. Fresh foreground `make check-all
PYTEST_WORKERS=4` completed successfully:13,015 backend tests,438 frontend tests,
coverage97.39%/97.69%, lint, formatting and typing green. Receipt:
`/tmp/qf-w43-s1-check320.log`. This resolves the matched-factor domain defect;
the separate source/native-product/projection limitations above remain.
