# FINDING-212: Duplicate price identities multiply a ranked leg

- **Status:** Corrected — duplicate original price identities refused by ADR-263
- **Date:** 2026-10-12
- **Severity:** High for direct public cross-sectional portfolio inputs
- **Scope:** Shared asset_returns original price-column identity
- **Decision:** ADR-263

## Evidence

Unique signals A=1/B=2 form short-A/long-B. Supply prices with labels A,A,B:
first row 100,100,100; next row 110,110,100. Both legs have price evidence and
all observations/returns are finite. Original weight projection repeats the
short-A weight onto both A columns and publishes [-0.003,-0.20000000000000018]
at quantile=0.5/cost=0.001. The same unique A,B evidence publishes
[-0.002,-0.10000000000000009]. Duplication breaks neutrality and inflates costs.
Direct asset_returns also emits both identical column identities as ordinary evidence.

Research-expert independently reproduced both results. Production dict-based panel
construction supplies unique symbols, and durable forward universes are unique.
No historical cohort, calibration or broker contamination is inferred. ADR-259's
membership guard correctly accepts both priced names and explicitly left duplicate
identity for separate review; this is not missing-price or score-precision recovery.

## Correction and required evidence

Refuse duplicate original price columns at shared asset_returns after existing
calendar checks and before price validation/arithmetic. Do not repair or choose
among duplicate observations. Duplicate axes with zero rows still have ambiguous
identity; unique zero-cell panels remain. Original unique arbitrary labels/order,
native dtypes, ranks/projection/lag/costs and error precedence stay unchanged.
Independent pre-code scope review approved this shared guard and empty-axis policy.
Longitudinal calibration identity remains unchanged; no thresholds or records move.

## Observed verification

Pre-implementation tests recorded 17 failures and 13 preserved cases. The
two-line source identity guard passed 413 affected tests. Independent final review
approved 152 focused tests, five exact native asset and 100 exact portfolio
baselines (float64/nullable/integer/wide prices, sparse/subset/reordered/empty
signals and native costs), nine strict duplicate-axis refusals and 135 exact
portfolio outputs across 16 generators/45 configurations. Canonical dict-based
construction retained unique columns. Caller inputs/error state and validation
precedence were preserved; removing the guard restores the parent source AST.

Initial focused lint rejected a test list-concatenation expression; an equivalent
list splat fixed lint without changing assertions. Fresh foreground
`make check-all PYTEST_WORKERS=4` passed: 5,316 backend tests at 97.75% coverage
and 363 frontend tests at 97.63% statement coverage; lint, formatting and type
checks passed.
