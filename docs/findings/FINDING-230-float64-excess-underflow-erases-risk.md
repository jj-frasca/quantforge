# FINDING-230: Float64 excess variance underflow erases risk

- **Status:** Corrected (ADR-281)
- **Date:** 2026-10-13
- **Review:** Codex autonomous session 8, ISO 2026-W42
- **Decision:** ADR-281
- **Prior art:** FINDING-113's explicitly remaining IR/tracking-error limits

## Finding and rejected repair

Native float64 and classic Float64 strategy [1e-200,2e-200,3e-200] versus zero
benchmark publish IR0/TE0 with finite alpha5.04e-198. Represented excess is
nonconstant: independent Fraction/Decimal800 gives IR31.74901573277509 and
TE1.5874507866387544e-199. Narrow ADR-279 and native wider ADR-272 do not cover
this remaining float64 sample-variance underflow. No historical contamination
is established and no generated records are changed.

Naive maxabs-normalized variance was rejected before implementation. Three
nextafter neighbors of1e-200 give a 17–21% IR/TE error against independent exact
observations because normalization rounds distinct near-constant levels. A
variance repair must not create another falsely measured coefficient.

## Correction and limits

ADR-281 recovers only collapsed/detected-underflow float64 or classic Float64
nonconstant excess dispersion. Anchored translated differences precede scaling;
original fsum plus separated exponents preserve IR independently of final rounded
risk. Original nonfinite dispersion refuses, unaffected native operation order
remains, and all other excess types retain their existing paths. No epsilon,
threshold, identity, schema, workflow or generated-record changes.

Final TE can legitimately be0 with nonzero IR (4096-row smallest-subnormal
fixture). Range safety does not establish universal correctly rounded moments:
pre-code exact midpoint audit found 6 one-ULP subnormal TE discrepancies among 448
property-domain cases and 15 among 1,138 wider cases, maximum 1 ULP. The draft property
was corrected BEFORE repository adoption to an exact Fraction squared midpoint
oracle and explicit 1 output ULP subnormal budget, preserving deterministic exact
fixtures and nonzero/sign assertions.309 independent midpoint/boundary checks
verified that oracle. Global mean-loss correction, original overflowing variance,
source-alpha strict-state behavior and already-rounded subtraction remain outside.

## Verification

Independent pre-code scope approved 326 Fraction/Decimal800 cases and final scratch
prototype 59 tests. Repository RED observed 53 genuine failures and 11 preserved
cases before implementation; focused new/prior tests passed 554 cases.

Final independent review approved the actual helper against 326 Fraction/Decimal800
cases, 629 targeted regressions and 309 exact midpoint/boundary oracle checks.
The 448-case production subnormal audit reproduced six deviations, maximum one
ULP, matching the written limit. Complete HEAD preservation passed 900 ordinary
comparisons (all scalars, excess metadata, inputs and strict state), plus 12
underflow cases with every non-risk output exactly preserved. Whole-module AST
restores after removing only new imports/helper/probe/recovery conditional.
Fresh foreground make check-all passed 10,079 backend and 363 frontend tests,
with 97.68% backend and 97.63% frontend statement coverage. Lint, format and strict
typing passed. Exact master CI is verified after publication.
