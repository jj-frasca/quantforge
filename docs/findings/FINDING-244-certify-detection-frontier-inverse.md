# FINDING-244: Detection frontier can report an unsupported or unconverged root

- **Status:** Resolved in the conditional frontier inverse
- **Date:** 2026-10-15
- **Scope:** Report-only conditional normal-model frontier
- **Governing decision:** ADR-292, extending ADR-043

## Reproduction

At executed `143b6729` (frontier identical to `a8054a5d`), the public solver
uses eight fixed iterations and a bounded erf-based inverse normal CDF.
Its defining equation is `s = b + z * sqrt((1 + s*s/504)/T)`, where `b` is
the unchanged ADR-018 bar and `z` the normal quantile of requested power.

| N | T years | Requested power | Reported s | Correct-quantile equation RHS |
|---|---:|---:|---:|---:|
| 200 | 2/252 | .99 | 689.5533274085002 | 839.0354924578209 |
| 200 | .01 | .95 | 120.73012896620799 | 122.52486353860647 |
| 1 | 4.3 | 1e-300 | -4.081206721171715 | -18.158510460911465 |

The first request has no finite solution to the original equation: its positive
quantile exceeds `sqrt(504*T)`. The second has a unique root near
127.16143937679657, but eight iterations have not converged. The third's unique
root is near -29.502877624789466; erf cancellation and the bounded quantile
search lose its lower tail. Conversely N200/T.01/p.001 has two equation roots;
a small residual alone cannot establish a unique frontier there.

These are directly reachable diagnostic-domain errors. The ordinary
N607/T4.3/p.8 control agrees with the independent equation. No actual graduate,
market-power effect or historical calibration invalidation is established.

## Adopted correction

ADR-292 supports only the open unique inverse domain `abs(z) < sqrt(504*T)`.
It preserves signed lower-power solutions and the existing below-two-symbol bar
convention. Boundary, nonunique and unattainable inverse requests refuse;
not every rejected lower-tail input lacks algebraic roots.

Use the standard-library inverse normal CDF without forming `1-p`. Exact
Fraction coefficients certify the sign of `a = 1-z*z/(504*T)`. Positive-quantile roots
use `(b+sqrt(D))/a`; negative-quantile roots use the rationalized
`(b*b-z*z/T)/(b+sqrt(D))`, with `D = b*b-a*(b*b-z*z/T)`.
Final square root/division run in an explicit independent Decimal160 context;
caller precision, rounding, traps and flags are preserved. Power .5 returns
the exact original bar. Nonfinite history/bar/root or unrepresentable unchanged
standard error refuses with ValueError. General scalar/count policy is separate.

This inverts a conditional iid-normal asymptotic single-bar model. It does not
certify the composite search/graduation pipeline's power or attribute every gap
to catalog capture. Qualify active descriptions accordingly. No threshold,
shared standard-error calculation, universe bar, search, reference scorer,
calibration identity or frozen cohort changes.

## Verification

Independent precode review approved 212 supported roots against Decimal350
monotone bisection (zero ULP differences), 28 unsupported/refused cases and
12 scientific quantile crosschecks. Receipt:
`/tmp/qf-w42-s15-frontier-precode-review.json`. The independent oracle solves
the unsquared equation by bisection; it does not mirror the quadratic solver.
Prior scratch work observed 33 failing /35 preserved tests before the prototype;
four caller-context failures then preceded the explicit independent Context fix.
These are scratch evidence, not a substitute for repository TDD.

Actual repository TDD observed 41 genuine failures /34 preserved cases before
production implementation (`/tmp/qf-w42-s15-red292.log`). All 75 original/new
frontier cases subsequently passed; Ruff lint/format and strict mypy passed.
All original 10 tests remain byte-for-byte intact. Permanent tests use independent
equation oracles, scientific quantile crosschecks and Hypothesis, without git
snapshots or source AST dependencies.

Independent actual-production review passed 212 Decimal350 roots (zero ULP
differences) and 28 refusals. Separate scratch source audits confirm exact shared
standard-error/bar source and AST, unchanged factory AST/schema fields/constant,
unchanged search/gate/calibration/accounting and preserved original test bytes.
Receipts: `/tmp/qf-w42-s15-frontier-production-review.json` and
`/tmp/qf-w42-s15-frontier-source-review.json`. Final six-path independent
review approved the implementation and documentation after 336 frontier, report,
null-calibration and accounting regression tests passed. Receipt:
`/tmp/qf-w42-s15-frontier-final-research-review.json`. Fresh foreground `make check-all PYTEST_WORKERS=8` passed 11,376 backend tests
at 97.34% coverage and 363 frontend tests at 97.63% statement coverage. All lint,
format and type checks passed. Terminal log: `/tmp/qf-w42-s15-check292.log`.
No universal correctly rounded transcendental-quantile/root claim is made.
