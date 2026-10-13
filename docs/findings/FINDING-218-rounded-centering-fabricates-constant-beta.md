# FINDING-218: Rounded moment centering fabricates constant-source beta

- **Status:** Corrected
- **Date:** 2026-10-12
- **Review:** Codex autonomous session 4, ISO 2026-W42
- **Decision:** ADR-269
- **Prior art:** separate constant-centering defect disclosed in FINDING-217

## Written finding and evidence

Strategy [.01,.02,.03] versus repeated benchmark [.1,.1,.1] publishes beta
.041666666666666664 (1/24). Rounded benchmark mean .10000000000000002 leaves
variance 2.8888949165808538e-34 and covariance 1.2037062152420224e-35. Reversing
the roles publishes beta 1.2037062152420224e-31 although constant strategy residuals
are exactly zero. Float64 and nullable Float64 reproduce both. No underflow is
signaled; ADR-268 intentionally leaves this separate defect unchanged.

An exact represented-input Fraction oracle gives zero covariance on either
constant side. A zero-variance benchmark invokes the existing beta-zero convention;
for constant strategy and nonconstant benchmark the quotient is mathematically zero.
These public synthetic examples do not establish historical market contamination.

## Narrow correction and qualifications

Use original aligned Series equality to identify exact constants before any beta
moments, then beta zero if either side is constant. Keep nonconstant beta arithmetic
and every downstream formula. Alpha changes naturally with corrected beta. No
float64 equality, tolerance, source alteration, threshold or generated-data rewrite.

Native wider distinct observations can collapse to equal float64 values; those
must remain nonconstant. A wider same-series example's existing beta about .880141
is a separate moment-precision limitation, retained in this slice. Other comparator
statistic/scale-restoration limitations remain; this is exact constant detection,
not universal covariance precision.

## Verification

Independent scratch prototype: 15 dtype/side constant cases yield zero, var/cov
spies confirm moment bypass, and 150 complete ordinary nonconstant outputs match
the published implementation exactly. Tests and ADR are written before production;
The pre-code run observed 15 genuine failures and 35 preserved cases, with
production unchanged. Original aligned source-equality guards were implemented
only afterward. All 140 affected benchmark/API tests pass, with lint/format green.
Independent final review approved 111 targeted tests and 240 complete exact
nonconstant baseline comparisons across five dtypes, two overlap patterns and
24 seeds. Three wider source panels that collapse under float64 conversion retain
their complete original results. Twelve native/nullable signed/unsigned constant
fixtures have beta zero and original alpha; three strict tiny same-series cases
retain beta one/alpha zero/caller state. Moment spies, source preservation and
Hypothesis tests pass. Removing only the guard and its two predicates restores
the original production AST. Foreground `make check-all PYTEST_WORKERS=4`
passed: 5,590 backend tests and 363 frontend tests, backend coverage 97.73% and
frontend statement coverage 97.63%, with all lint/type/format checks green. Exact
master CI is checked after individual delivery.
