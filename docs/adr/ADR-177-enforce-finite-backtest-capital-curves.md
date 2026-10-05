# ADR-177: Enforce finite backtest capital curves

- **Status:** Accepted
- **Date:** 2026-10-05
- **Deciders:** Codex autonomous session 1, ISO 2026-W41
- **Resolves:** FINDING-109
- **Extends:** ADR-007, ADR-110

## Context

Constructor sign checks admit NaN/infinite capital or cost. Return-based metrics cannot detect
nonfinite or zero capital-scaled curve values, even with valid positive finite initial capital.

## Options Considered

1. Require finite config and finite positive computed equity before publication. This preserves
   representable observations and declines undefined wealth.
2. Cap capital/cost or floor the curve. Arbitrary bounds change the research result.
3. Rely on return metrics alone. They do not describe scaled-wealth representability.

## Decision

Require finite `initial_capital > 0` and finite `cost_rate >= 0` in construction. Compute the
existing cumulative-product curve unchanged, locally suppressing overflow/underflow warnings,
then reject any nonfinite or nonpositive equity value before constructing BacktestResult.
Retain zero costs, empty histories, accepted extreme representable wealth, and the original
position/lag/turnover/net/metric formulas. No upper capital or cost cap is introduced.

## Consequences and limits

A published research result cannot pair finite return metrics with nonfinite or zero scaled
wealth. Valid inputs can deliberately raise when their output cannot be represented. Empty curves
remain accepted. The guard also catches later public capital mutation for nonempty runs; it does
not freeze the engine configuration or validate every other input/artifact boundary.
Research wealth stays distinct from observed broker insolvency, which ADR-169 retains honestly.
No generated data, validation threshold, estimator, API schema or workflow changes.

## Reversal

Remove finite constructor/output checks. This reopens FINDING-109.
