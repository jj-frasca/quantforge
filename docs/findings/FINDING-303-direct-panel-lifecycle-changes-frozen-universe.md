# FINDING-303: Direct panel lifecycle evaluation changes the frozen universe

- **Status:** Corrected by ADR-363
- **Date:** 2026-10-24
- **Severity:** Medium — direct lifecycle evidence can describe a different factor
- **Scope:** `evaluate_cross_sectional_lifecycle` ordered panel identity
- **Prior art:** ADR-025, ADR-140, ADR-252 / FINDING-201

## Evidence

A direct lifecycle call accepts a subset, substituted symbol, or reordered panel
under an unchanged position. `score_forward` rejects those same panels under
ADR-252. Lifecycle evaluation reconstructs both the ranked factor and equal-weight
benchmark from the supplied panel without checking its frozen columns.

Deterministic witness: NumPy `default_rng(0)`, 800 by 6 daily returns drawn from
Normal(0.0002, 0.01), prices `100 * cumprod(1 + returns)`, business dates from
2015-01-01 UTC, columns S0 through S5. Freeze momentum lookback126/skip0/quantile0.2
at row400, cost0.001, and use the unchanged default exit policy. The complete panel
returns rolling factor Sharpe -3.7339602658692472, drawdown0.4548054162760148 and
benchmark Sharpe1.852819687629644. Supplying only S0 through S3 instead returns
-3.7976386034207676, 0.6011055156175467 and 1.2333079288765803. Both retire, but
their statistics and reasons describe different universes under the same position.
Replacing S0 with OUTSIDE or reversing the columns is also accepted. Equal numbers
on those two witnesses do not establish column-order invariance; ADR-257 retains
ordered-universe tie handling. The no-forward shortcut accepts drift as well.

Independent eight-row witness: UTC daily dates January1–8, freeze January3,
`xs_value`, values A1/B0.8/C0.2/D0, quantile0.25 and cost0.001. A prices are
`100*cumprod([1,1.01,1.03,1.01,1.03,1.01,1.03,1.01])`, C prices use
`[1,0.99,0.97,0.99,0.97,0.99,0.97,0.99]`, and B/D stay100. With grace0,
rolling window3, benchmark requirement disabled and all other policy defaults,
the complete panel holds (rolling Sharpe22.912878474779202, drawdown0).
Subset C/D retires (Sharpe-22.912878474779244, drawdown0.08704567090000026).
Replacing A with E also retires (Sharpe0). Reversed columns still hold; this
establishes accepted identity drift, not a numerical permutation effect.

The managed book already validates exact dataset membership and aligned panel
order before scoring and evaluation. This is a direct synthetic boundary defect,
not evidence of a corrupted generated book, actual lifecycle action, affected
graduate, broker order, or false graduation. No search or calibration was run.

## Correction and verification

Require the exact existing scorer column comparison at the direct lifecycle
boundary after policy revalidation and before calendar access. Refuse drift,
including no-forward calls, without changing or repairing supplied prices.
Preserve matching-panel decisions, all lifecycle defaults and thresholds,
reconstruction, benchmark arithmetic, calendars, schemas and managed acquisition.

Nineteen regressions failed before implementation while four controls passed.
After the two-line entry guard, all188 focused tests pass, including23 new tests
and Hypothesis permutation checks. Independent final research review approves
all23 new tests, exact preservation of96 prepatch native decisions across four
factors, zero/grace/measured windows, two costs, complete/partial static maps and
oscillating/tied prices, plus caller nonmutation. Removing only the new guard
restores the entire prior module AST. These bounded controls do not certify
arbitrary floating-point behavior or source provenance.

The full foreground `make check-all PYTEST_WORKERS=2` passes:14,598 backend and746
frontend tests,97.41% and97.88% statement coverage respectively, lint, format and
strict typing. No threshold, policy hash, schema, generated record, frozen cohort
or longitudinal accounting-v14 identity changes.
