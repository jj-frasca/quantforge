# FINDING-203: Cross-sectional returns hide invalid source prices

- **Status:** Corrected
- **Date:** 2026-10-11
- **Severity:** High — invalid raw prices become finite portfolio evidence
- **Scope:** asset_returns and portfolio_returns propagation
- **Decision:** ADR-254
- **Prior art:** ADR-178/FINDING-110

## Evidence

Independent raw-panel reproduction: A=[100,NaN,110], B=[100,100,100] produces
A returns [0,0,0]. A=[-100,-110,-121] produces [0,0.1,0.1] and a long-A/short-B
portfolio [-0.002,0.1,0.1]. A singleton zero or missing price produces a zero asset
return and finite portfolio output. The first-row zero and missing-value filling
hide invalid original evidence before portfolio aggregation. Complex prices also
produce finite complex return values instead of source refusal.

ResearchDataset protects quality-gated production prices. These are direct synthetic
reproductions, not an observed bad stored book, measured false graduate or real
cohort result. No workflow, search, broker or generated record was changed.

## Correction and verification

ADR-254 applies ADR-178's intrinsic dtype/domain policy to populated cross-sectional
panels at asset_returns, preserving native precision instead of coercing to float64.
Independent pre-code review preserves seven exact native/nullable/wide-integer/
longdouble/empty-panel comparisons and passes 152 existing engine/forward tests
under a scratch wrapper.

Before implementation, 26 refusal regressions failed and eight preservation cases
passed. The baseline already refused string/boolean payloads with TypeError; those
cases normalize the boundary error and do not represent newly prevented fabricated
output. All 227 affected engine, forward, search and IC tests pass after correction.
Independent final review approves seven exact complete native asset-return and 28
portfolio-return comparisons, including mixed nullable numeric, extreme uint64,
longdouble prices above float64 range, valid singleton/zero-cell panels, all-missing
signals and zero/nonzero costs. Caller prices remain unchanged. Removing the guard
and its imports restores the complete published-module AST. A Hypothesis property
checks positive-price-scale invariance. The full foreground gate passes
5,139 backend and 363 frontend tests, with 97.78% backend and
97.63% frontend statement coverage; lint and strict typing pass. No fill/drop/repair, source calendar, cost, signal,
estimator, schema or threshold changes. Derived overflow remains separate.
