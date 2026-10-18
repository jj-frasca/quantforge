# FINDING-266: Holdout product hides intermediate insolvency

- **Date:** 2026-10-18
- **Severity:** High for scored wealth interpretation
- **Status:** Resolved by ADR-315 scored-period wealth guard
- **Reviewed source:** 9eca707c, cross_sectional/search.py::_score_holdout

## Evidence

A fixed xs_value signal on two names ranks LONG above SHORT. With positive
prices LONG=[100,100,100], SHORT=[100,400,1600], quantile=.5 and cost=.001, the
unmodified public portfolio kernel returns [-.002,-3,-3]. Scoring the last two
bars multiplies (1-3)*(1-3)=4 and publishes total_return3, Sharpe0, n_bars2.
Intermediate unit wealth is -2 before the apparent recovery to4. The same path's
public forward scoring refuses its negative equity point.

The parent independently inserts an initial flat bar into a four-date panel,
obtains raw returns [-.002,0,-3,-3] and reproduces the same accepted holdout +3.
Exact integer/Fraction multiplication confirms the sign path. These hand-built
fixed-score witnesses use no parameter search, random source, calibration or
vendor. No production occurrence, false graduate or revised historical outcome
is established. The two-loss witness's Sharpe0 would fail the existing Sharpe bar;
it demonstrates an invalid scored return claim, not a passing composite gate.

Independent receipt /tmp/qf-w42-s31-xs-wealth-review.{md,py,json}; parent
/tmp/qf-w42-s31-xs-wealth-parent.json. ADR-258 explicitly leaves wealth-domain
policy outside the raw return kernel. The aggregate gate check under ADR-301
requires total_return>-1 but cannot infer intermediate wealth from the product.

## Governed correction

ADR-315 refuses native scored holdout returns <=-1 before benchmark preparation,
products or scores. Raw leveraged-loss reporting, out-of-slice warmup, original
valid formulas and all gate thresholds remain. No liquidation rule, full-prefix
account guarantee, aggregate projection recovery or historical rewrite is added.

Before implementation, 180 valid configured HoldoutScore payloads were frozen
from all45 registry configurations, two cuts and two costs on a fixed panel:
/tmp/qf-w42-s31-holdout-valid-baseline.json, semantic payload SHA256
51aac956b30d1c4afa63d70f78969e02da71653397d3796c0238c24b4ac91839.
These are direct score controls, not a calibration cohort or power measurement.

## Verification

Actual pre-implementation RED: 10 failed, five preserved in 2.55s, before any
production edit (/tmp/qf-w42-s31-wealth-red-final.log). Independent precode review
approved the ADR, finding and 15 cases. After the two-line guard, 165 focused
cases passed in 18.07s, including all 15 new cases and existing search/kernel
tests. The 180 prechange configured score payloads compare exactly, retaining
their recorded semantic SHA256.

The first focused run had 164 passes and one fixture failure: pandas inferred
float64 and narrowed a longdouble value above -1 to exactly -1 before scoring.
The guard correctly refused that represented value. The fixture now supplies
explicit native dtype and asserts exact stored scalar identity; this precision
refinement occurred after implementation and is not claimed as precode TDD.
Production code and all original assertions remained unchanged.

Independent final six-path review approved the correction and independently
passed all 15 cases. Removing only the new two-line If restores the entire
original module AST, including signatures, docstrings and mathematical operations.
Receipt /tmp/qf-w42-s31-holdout-wealth-independent-review.json; source SHA256
8d341417caa4c9e9f33cf6d9e4580877228fb9feaf82cd784a09a12622c8c90a.
Fresh foreground make check-all passed 12,881 backend cases (97.39% coverage)
and 438 frontend cases (97.69% statements), including lint, formatting and strict
types. Log /tmp/qf-w42-s31-check315.log; all local verification closed successfully.
Exact master CI is verified after individual publication.
