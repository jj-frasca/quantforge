# FINDING-301: Zero forward turnover hides measured inherited exposure

- **Date:** 2026-10-24
- **Review:** Codex autonomous session 29, ISO 2026-W43
- **Status:** Resolved by ADR-361 for observed nonzero forward return paths
- **Area:** Single-name paper lifecycle, ADR-073

## Finding and deterministic witness

`_forward_trades` counts position changes within the forward window. Zero such
changes does not imply zero exposure or zero forward returns: the warmed strategy
may already hold a nonflat position at the freeze boundary. Nevertheless,
`lifecycle_from_returns` bypasses every performance/risk predicate when the count
is zero and reports zero statistics with an unmeasured/never-traded reason.

At revision `847f7d01`, use the public `BacktestEngine` and default
`MomentumStrategy(lookback=60, skip=5)` on deterministic closes constructed from
300 returns of +1%, followed by -35% and `[0.009, 0.011] * 25`.
Open/high/low equal close, volume is 1000, and the unique calendar is UTC daily.
Freeze at row 299, after the strategy has become long. The 51 forward rows all
have position +1, zero forward turnover events, and nonzero returns. The first
forward return is exactly -0.35. With the actual zero trade count and default
ExitPolicy, the lifecycle reports hold, zero drawdown and "not yet measurable
(0 trades in 51 forward bars)". Feeding the identical return paths with a count
of one as a counterfactual control reports drawdown 0.35 and exit under the
unchanged 25% risk limit (also the unchanged benchmark comparison).

Receipt: `/tmp/qf-w43-s29-inherited-exposure-prospective.json`.
No RNG, vendor, search, calibration, cohort, broker or generated data is involved.
An independent public-wrapper review also reproduced the bypass with lookback252
and with three actual coarse-grid lookback250/skip0,30,60 configurations after
400 pre-freeze increments. Receipt: `/tmp/qf-w43-s29-carry-position-review.json`.

## Scope and decision requirements

This contradicts ADR-073's inference that zero forward trades necessarily means
an all-zero forward return path. It does not dispute the need to protect genuinely
inactive, all-zero paths from manufactured Sharpe verdicts. ADR-356's inception
baseline is downstream of this early branch and therefore cannot repair it.
This establishes a reachable public-engine lifecycle bypass, not an affected
historical paper position, account loss or production broker action.

A prospective correction must retain genuine no-evidence behavior, original
trade counts, grace, every threshold/default and generated history. Distinguish
observed nonzero forward returns from absence of forward turnover without
fabricating an entry trade. Independent review, an ADR before implementation,
actual failing tests and full gates are required. Exposure with all-zero returns
and account entry/switching reconciliation need explicit scope rather than an
invented execution history. The zero-count `beats_buy_and_hold` suppression in
`evaluate_forward` deserves separate consideration under the same distinction.

## Correction and verification

ADR-361 limits the no-evidence branch to zero turnover plus all-zero original
forward returns and permits the existing strict score comparison with turnover
or any nonzero forward return. Actual counts, every threshold/default and grace
remain. The default Momentum public engine/wrapper risk witness and a public
dataset-backed inherited-short score witness cover both consumers. The latter
has zero forward turnover, positive forward Sharpe and negative benchmark Sharpe,
but previously reported `beats_buy_and_hold=False` solely because of its count.

Before the source patch, new tests plus the two strengthened ADR-356 zero-count
loss scenarios produced 25 genuine failures and 49 controls in 4.91s. No test was
deleted or skipped. After the two-condition patch, 198 focused tests passed in
4.01s; additional inactive-public-score and strict-default-limit controls were
then added. Final independent focused verification passed all 200 tests, including
38 new cases. Hypothesis checks drawdown against exact Fraction wealth paths,
including offsetting-return evidence. Independent final research review approved
the source, tests and bounded claims. Parent and independent whole-module AST
comparisons found exactly the two prescribed condition changes and lifecycle
docstring change; defaults, thresholds, counts and schemas are unchanged. Another
244 original lifecycle controls matched the prior outputs exactly, including
inactive paths and ordinary nonzero-count decisions. Source SHA256:
`809ea341e1c5a6f00097d0735234b1115ab01012b5e1b093b4ab93744ca54d7e`.

Fresh foreground `make check-all PYTEST_WORKERS=2` passed: 14,575 backend tests
(97.41% coverage), 736 frontend tests (97.88% statements), lint, formatting and
type checks. Receipts: `/tmp/qf-w43-s29-check361.log`,
`/tmp/qf-w43-s29-turnover-preservation.json` and
`/tmp/qf-w43-s29-adr361-independent-review.json`. No production occurrence or
account-execution claim follows, and no generated/frozen evidence was modified.
