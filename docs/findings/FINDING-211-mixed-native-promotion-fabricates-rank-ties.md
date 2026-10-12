# FINDING-211: Mixed native numeric promotion fabricates rank ties

- **Status:** Corrected — mixed native numeric order preserved by ADR-262
- **Date:** 2026-10-12
- **Severity:** High for supported public mixed native numeric panels
- **Scope:** Shared cross-sectional long_short_weights rank input
- **Decision:** ADR-262

## Evidence

With separate native columns in supplied A,B order, int64 A=2**53+1 exceeds
float64 B=2**53 exactly, but pandas ranks A=1/B=2. uint64 A=2**63+1 versus
float64 B=2**63 also reverses; uint64 A=2**63 versus int64 B=2**63-1 shows
that no floating source column is necessary. The common numeric array loses
integer precision through floating promotion. The original ranker shorts the
higher score and longs the lower; ordinary prices A=100→110, B=100→100 then
publish -0.10 on the next bar instead of native-order +0.10.

Independent review reproduced all three cases. Evidence uses exact Fraction
integer/represented-float comparisons: a direct NumPy integer-versus-float
comparison can itself promote and lose the distinction. Object ranking matched
1,000 independent exact stable-order panels; original ranking lost order on 655.
Homogeneous int64/uint64 and nullable Int64/UInt64 remain correct (200 independent
large-integer baselines); extension mixed and integer/Decimal/Fraction inputs
already retain exact order. No historical production or calibration contamination
is inferred, and this remains separate from ADR-261's wide-floating correction.

## Correction and required evidence

Object-rank only native mixed integer/float or signed/unsigned numeric panels,
retaining original true tie/missing/count/weight/return/cost rules and all other
paths. Independent pre-code review approved 1,000 exact rational panels under
strict NumPy state, unchanged caller inputs, ten preserved supported paths and
all 16 generators/45 configurations. Small mixed numeric dtypes share that path
without value thresholds; document the object-ranking performance tradeoff.
Longitudinal calibration identity stays unchanged for ADR-262's stated reasons.
Already-rounded scores and arbitrary unsupported payloads remain unclaimed.

## Observed verification

Pre-implementation tests recorded seven failures and 19 preserved cases. The
narrow mixed-native correction passed 370 affected tests. Independent final review
approved 198 focused tests, 1,000 exact rational mixed-order oracle panels under
strict NumPy state, 22 preserved supported outputs or exact exceptions, 100 exact
ADR-261 wide outputs, and 135 exact outputs across 16 generators/45 configurations
(three quantiles each). Caller inputs/error state were unchanged. Removing only
the mixed-native selection restores the ADR-261 parent source AST exactly.

Fresh foreground `make check-all PYTEST_WORKERS=4` passed: 5,286 backend
tests at 97.75% coverage and 363 frontend tests at 97.63% statement coverage;
lint, formatting and type checks passed.
