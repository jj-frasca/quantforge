# FINDING-217: Positive benchmark moments still publish wrong beta

- **Status:** Corrected for native beta underflow; separate centering limitation remains
- **Date:** 2026-10-12
- **Review:** Codex autonomous session 4, ISO 2026-W42
- **Decision:** ADR-268
- **Prior art:** explicitly remaining beta scope of FINDING-113/ADR-181

## Written finding and reproduction

For represented float64 returns [1,2,3] times the stated scales, the comparator
publishes finite wrong beta despite positive native benchmark variance:

| Benchmark scale | Strategy scale | Native variance | Native covariance | Published beta | Exact beta |
|---|---|---|---|---|---|
| 2e-162 | 1e-162 | 5e-324 | 0 | 0 | 0.5 |
| 3e-162 | 1e-162 | 1e-323 | 5e-324 | 0.5 | 1/3 |
| 1e-100 | 1e-230 | 1e-200 | 0 | 0 | about 1e-130 |

The oracle converts each actual source float to Fraction, centers and sums exact
covariance and variance, then rounds only the final quotient. It does not assume
intended scale ratios survived source rounding. Both parent and independent
research-expert reproduced these results; all published fields remain finite.
ADR-180's finite guard cannot detect the loss, and ADR-181's variance==0 trigger
never enters recovery. These are public synthetic kernel defects, not evidence
that historical market results were contaminated.

## Narrow correction and limits

Detect underflow only in the native beta variance/covariance/quotient and reuse the
existing scaled covariance ratio for nonconstant benchmarks. Preserve native beta
otherwise, true-constant conventions and all original downstream formulas. No
variance epsilon, source repair, threshold or generated-record change is authorized.

Existing scaled recovery is not a universal precision guarantee. Other comparator
statistics and extreme scale-restoration limitations remain separate, including
strict-state underflow in excess dispersion for nonidentical tiny series. Alpha
uses its original formula with corrected beta; there is no new alpha estimator.

## Verification

Independent scratch prototype recovers five affine cases against exact Fraction
oracles, preserves five true constants and 100 ordinary complete baseline outputs,
and retains strict same-series neutrality/caller state. Production is unchanged;
The initial pre-code run had 19 failures and seven passes. One preservation fixture
revealed a separate native centering limitation: strategy [.01,.02,.03] versus
constant benchmark [.1,.1,.1] publishes beta 1/24 because rounded centering leaves
a positive normal residual variance. No underflow is signaled; that defect remains
unbundled and unchanged. The preservation fixture now uses exact binary .125
with the same beta-zero assertion. Final pre-code verification recorded 18 genuine failures and 11 preserved cases.
The native underflow trigger was implemented only afterward. All 119 affected
benchmark/API tests now pass; lint/format pass. Independent final review approved 90 targeted tests and 246 complete exact
published-baseline comparisons across four dtypes, two overlap patterns, 30 seeds
and six constant baselines. Production AST restores to the published module after
removing only the scoped native-beta change. The .1 native centering baseline and
two exact-zero-covariance probes remain unchanged. Foreground
`make check-all PYTEST_WORKERS=4` passed: 5,569 backend tests, 363 frontend tests,
97.74% backend coverage and 97.63% frontend statement coverage, with all lint/type/
format checks green. Exact master CI is checked after delivery.
