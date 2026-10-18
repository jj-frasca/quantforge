# FINDING-122: Extreme-scale risk ratios return degenerate zero

- **Date:** 2026-10-07
- **Severity:** Low — extreme finite scale collapses native risk arithmetic
- **Status:** Resolved by ADR-203/205 native-failure recovery; later precision limits remain

## Original evidence (before ADR-203/205)

sharpe_ratio([1,2,3,4]) is approximately 30.740852 while the same values scaled by 1e-200 or
1e200 return 0.0. Native sample variance underflows or overflows, entering the degenerate fallback.
sortino_ratio([1,-2,3]) is approximately 9.165151; scaling by either factor likewise returns zero
with default target zero. True risk variation has not disappeared. Source-validity fixes do not
address this finite-arithmetic behavior. Large-scale arithmetic can also emit overflow warnings.

## Original next action and limits (historical)

Investigate scale-safe evaluation with independent high-precision oracles before modifying native
fallback conventions. Distinguish genuine constant/no-downside samples from collapsed arithmetic,
and preserve ordinary-scale estimator semantics. These scales are far from normal market evidence;
no observed production misclassification is claimed. No thresholds or generated records change.

## Status reconciliation — 2026-10-18

The Open header outlasted the accepted and implemented recovery decisions.
ADR-203 (`1a9e780c`) recovers failed native sample-Sharpe arithmetic rather than
calling nonconstant observations flat; ADR-205 (`8eec4e4a`) recovers Sortino
failures and represents still-unmeasurable descriptive ratios as None. Subsequent
precision refinements remain separately attributed in the metric contracts.
This closes the reported scale-collapse defect, not every numerical-accuracy question.

Parent replay of the original six cases (two metrics at scales 1, 1e-200 and
1e200) matched independent 90-digit Decimal oracles on the actual represented
float observations within absolute 1e-12. Sharpe outputs are approximately
30.74085229787879; Sortino outputs approximately 9.16515138991168, including both
extreme scales. No case returns the former fabricated zero. Receipt:
`/tmp/qf-w42-s30-f122-parent.json`.

Independent research review reproduced all six against 800-digit Decimal
oracles within relative 1e-14, under strict NumPy policy with no public-call
warnings. Genuine constant Sharpe and no-downside Sortino retain intentional
zero; an unrepresentable Sortino control retains None. Review:
`/tmp/qf-w42-s30-stale-finding-review.md`. These are bounded hand-built probes,
not a universal precision certificate or an observed production-impact claim.
No estimator, threshold, identity, generated record or historical measurement is
changed by this status correction. Full verification is recorded below.

Independent final review approved this documentation-only reconciliation. Fresh
full foreground `make check-all PYTEST_WORKERS=4` passed 12,787 backend tests
(97.39% coverage) and 438 frontend tests (97.69% statements), with lint, formatting
and strict types green. Receipt: `/tmp/qf-w42-s30-check-status.log`. Only these two
finding documents change; production, frontend, tests and generated records stay
byte-identical. Exact master CI is verified after individual publication.
