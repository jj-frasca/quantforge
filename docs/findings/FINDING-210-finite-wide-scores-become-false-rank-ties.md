# FINDING-210: Finite wide scores become fabricated rank ties

- **Status:** Corrected — native wide score order preserved by ADR-261
- **Date:** 2026-10-12
- **Severity:** High for supported public wide numeric inputs
- **Scope:** Shared cross-sectional long_short_weights rank input
- **Decision:** ADR-261

## Evidence

On NumPy 2.5.3/pandas 3.0.6 with 63 native longdouble mantissa bits,
finite scores A=2e400 > B=1e400 rank as A=1/B=2 in supplied A,B order.
The same failure occurs without overflow or warning at
A=1.000000000000000001 > B=1. Native observations are distinct, but pandas'
numeric rank path casts to float64, fabricating ties. The original shared ranker
shorts A/longs B. Ordinary prices A=100→110, B=100→100 then publish approximately
-0.10 on the next bar where native-order long-A/short-B requires +0.10.

Research-expert independently reproduced both cases. No historical cohort,
calibration, graduate or broker contamination is inferred. ADR-260/F209 correctly
refuses original infinities and explicitly leaves finite precision unclaimed;
its existing ascending wide fixture happens to agree with supplied-order ties.

## Correction and required evidence

Choose pandas object ranking only for panels containing a native floating dtype
wider than float64. This retains native scalars and avoids the narrowing rank path;
ordinary inputs retain their existing call. All count/weight/return formulas remain.
Independent scope review matched 1,000 seeded wide panels to a native-scalar stable
sort oracle, including missing values and real ties. True ties keep ADR-257's
supplied order. Object/nullable/bool compatibility and exact standard generator
outputs remain; arbitrary mixed integer/float precision is a separate limitation.

Calibration identity is unchanged for the reasons in ADR-261: this ranker is not in
the longitudinal calibrated pipeline and canonical production generators retain
float64 scores. No threshold, generated record, estimator recovery or API change.

## Observed verification

Pre-implementation tests recorded 11 failures and six preserved cases. The
conditional rank-input correction passed 344 affected tests. Independent final
review approved 172 focused tests, 1,000 native stable-order oracle panels under
strict NumPy state, 75 exact ordinary baseline outputs and all 45 configurations
across 16 shipped generators (three quantiles each). Caller state was unchanged.
Additional true subnormal, signed-zero tie, all-missing and mixed nullable probes
passed; removing the rank-input selection restores the original source AST.

The first full gate stopped on formatting before tests; source formatting was
corrected without behavior changes. The fresh foreground `make check-all
PYTEST_WORKERS=4` passed: 5,260 backend tests at 97.75% coverage and 363 frontend
tests at 97.63% statement coverage; lint, formatting and type checks passed.
