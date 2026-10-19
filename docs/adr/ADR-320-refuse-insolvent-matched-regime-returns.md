# ADR-320: Refuse insolvent matched regime returns

- **Status:** Accepted
- **Date:** 2026-10-18
- **Deciders:** Codex autonomous session 33, ISO 2026-W42
- **Extends:** ADR-012/110/177/315/318/319
- **Resolves:** FINDING-271

## Context

The regime helper compounds selected gross return factors without checking
individual matched returns. On flat ordered market prices, [-3,-3] produces
intermediate unit wealth-2 and terminal wealth4, published as total_return3.
RegimeBreakdownEntry accepts that finite positive claim. The separate [-2,-3]
witness reports1. Normal BacktestEngine enforces positive finite wealth, so
no affected production report, search, calibration or false graduate is
established. Retrospective partitions are not executable switching accounts,
but that does not justify reviving negative gross factors into positive returns.

## Decision

Immediately after the existing inner alignment, refuse when any native matched
strategy return is <=-1.0. Raise ValueError before market pct_change, labels,
groups, products or Sharpe. Use the native Series comparison without Float64
coercion, clipping, liquidation, stopping or source repair.

Preserve original window and both calendar guard precedence, default20, zero
horizons and all alignment/label/group/product/Sharpe statements. Unsafe
returns outside the matched intersection do not trigger this scored-domain
guard; disjoint or empty matched sources retain empty results. Do not change
the engine's faithful raw-return surfaces or existing report models.

This guard does not promise full original-value/dtype validation, market-price
validity, finite arithmetic recovery, aggregate projection recovery or an
account ledger. Existing downstream Sharpe checks still refuse missing,
nonfinite and unsupported matched numeric evidence where they already did.
Native products may still overflow/underflow or round an aggregate return to-1.
No report schema, selection rule, gate threshold, search identity, v14,
generated record or frozen cohort change.

## Options considered

1. Guard native matched returns before all scoring.
   Chosen: stops unsupported gross factors without changing solvent arithmetic.
2. Check only aggregate total_return>-1.
   Rejected: both demonstrated revived paths have positive terminal returns.
3. Reject every original unsafe return before alignment.
   Rejected: broadens the preserved matched-intersection scoring policy.
4. Invent liquidation/stopping or floor wealth.
   Rejected: creates an execution policy rather than reporting supplied evidence.

## Verification and reversal

Observe RED before source edits for real public-helper negative-factor revival,
exact bankruptcy and first/interior/last matched unsafe returns. Assert refusal
before market calculations, grouping and Sharpe, preserving count/calendar
precedence. Keep empty/disjoint and unmatched-unsafe controls, original native
values immediately above/below-1 and bounded solvent-path financial properties.
Twenty-four valid pre-edit payloads are frozen. Source AST must match the
complete prior module after removing only the two-line guard and restoring
its docstring. Independent review and foreground full gates precede individual
push and exact CI. Removing the guard reopens FINDING-271; keep this evidence.
