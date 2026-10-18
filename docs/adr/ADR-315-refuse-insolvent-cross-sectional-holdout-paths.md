# ADR-315: Refuse insolvent cross-sectional holdout paths

- **Status:** Accepted
- **Date:** 2026-10-18
- **Deciders:** Codex autonomous session 31, ISO 2026-W42
- **Resolves:** FINDING-266
- **Extends:** ADR-024/016
- **Relates to:** ADR-110/177/258/301

## Context

The cross-sectional holdout scorer multiplies gross return factors without
checking each scored period's wealth domain. Two returns of -3 produce positive
terminal growth4 after intermediate wealth-2. This synthetic direct scorer
publishes total_return3; the gate's aggregate total_return>-1 guard cannot
detect that intermediate insolvency. Forward equity points already refuse it.
No affected production result, false graduate or calibration is established.

## Options Considered

1. Refuse scored holdout returns at or below -1 before aggregation.
   - Pro: enforces the positive-wealth interpretation where it is claimed.
   - Con: previously accepted insolvent holdout paths now raise.
2. Impose a new wealth-domain rule on the raw portfolio return kernel.
   - Pro: rejects such series at every consumer.
   - Con: expands ADR-258's deliberately limited contract and suppresses faithful
     reporting of raw leveraged losses; unrelated consumers need separate review.
3. Clamp losses, stop the path, or repair negative wealth.
   - Pro: could return a scalar for every path.
   - Con: invents liquidation/margin policy and changes the submitted strategy.

## Decision

In cross_sectional/search.py::_score_holdout, immediately after selecting
full_port.loc[holdout.index], refuse when any native scored return is <= -1.0.
Raise ValueError before benchmark preparation, product aggregation or Sharpe.
Do not coerce to float or replace values before this comparison. The unchanged
raw kernel already validates complete finite return evidence.

Keep the original full-panel warmup call, slice selection, equal-weight benchmark,
product, score, count and Sharpe operations for valid inputs. Unsafe returns only
outside the scored slice do not trigger this new guard. Preserve raw portfolio
returns, including faithful losses <=-1; no universal account ledger, full-prefix
positive-equity or liquidation policy is introduced. Do not change the aggregate
holdout schema or existing gate predicates.

This is an intrinsic scored-wealth domain, not a new Sharpe/cost/gate threshold.
No estimator, grid, selection, longitudinal calibration identity, accounting-v14,
generated record or frozen-cohort change. Compounding underflow/overflow and
aggregate binary64 return projection retain their existing separate limitations.

## Verification and consequences

Observe actual real-kernel negative-factor and exact-bankruptcy RED before source
edits. Cover first/interior/last holdout loss, refusal before benchmark/scoring,
unchanged out-of-slice warmup and empty-slice behavior. Test original native
Fraction/wider values around -1 without claiming they are actual kernel outputs;
include Hypothesis bounded solvent-path product controls. Preserve the prechange
180 configured score payloads exactly and independently review the single guard.
Run foreground make check-all and exact post-push CI. Valid near-boundary native
values may still yield an aggregate float rounded to -1; this correction promises
no new aggregate projection recovery.

## Reversal

Remove the scored-slice guard and reopen FINDING-266. That restores positive
terminal claims after an intermediate negative-wealth period and is not recommended.
