# ADR-258: Enforce finite cross-sectional fee accounting

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 35, ISO 2026-W41
- **Resolves:** FINDING-207
- **Relates to:** ADR-024, ADR-177, ADR-232, ADR-256

## Context

portfolio_returns only compares cost_rate with zero. NaN and positive infinity
can publish nonfinite net returns, including zero-exposure histories. A finite
1e308 cost overflows when both legs reverse. Downstream Sharpe already refuses
nonfinite returns, but the public kernel itself publishes them.

## Options Considered

1. Validate native cost finiteness and final native net returns; refuse overflow.
2. Convert costs/results to float64, cap costs or substitute zero returns. These
   alter native accounting or reject previously valid empty wide-cost histories.
3. Rely on downstream metrics. Direct callers can still receive nonfinite returns.

## Decision

Require finite cost evidence while retaining the original negative comparison and
cost operand. Use native scalar finiteness, with exact Rational and Decimal
finiteness when NumPy does not support their scalar types. This is a finite-source
policy, not a new nonboolean or float-representability policy: previously valid
bool/Fraction costs and empty histories with finite wide costs remain accepted.
Keep ranking, lag, turnover and net formulas unchanged. Before returning, require
all native net values finite, including object-dtype Fraction accounting without
coercing the result. Normalize native OverflowError/FloatingPointError to ValueError.
Retain caller NumPy error state, zero cost, huge finite cost with representable flat
outputs and empty outputs. Original unsupported mixed arithmetic remains unsupported.

## Verification and limits

Observe source-cost and derived-overflow RED tests before code. Preserve native
cost/dtype behavior and independent scalar two-leg turnover accounting; test empty,
zero exposure, reversing exposure, native arithmetic exceptions and error state.
Require independent review and full foreground make check-all before publication.
No cost cap, wealth-domain policy, signal policy, estimator, threshold or generated
record changes. No revised graduate, calibration or false-zero Sharpe is inferred.

## Reversal

Remove source and net finiteness guards and arithmetic exception normalization.
This reopens FINDING-207.
