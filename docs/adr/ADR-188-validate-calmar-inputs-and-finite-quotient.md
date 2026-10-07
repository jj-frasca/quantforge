# ADR-188: Validate Calmar inputs and finite quotient

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 11, ISO 2026-W41
- **Resolves:** FINDING-121, FINDING-123
- **Extends:** ADR-108, ADR-110, ADR-187

## Context

Calmar's zero-drawdown shortcut hides invalid annualized-return inputs. Its division also emits
infinity for finite scalars, including a complete positive-wealth BacktestMetrics sample where
all other fields are finite (FINDING-123). The sole production caller composes existing metrics;
no intended invalid-scalar or nonfinite-output contract was found.

## Options Considered

1. Validate both original scalars before shortcuts and decline nonfinite quotients.
2. Cap overflow or substitute zero. Invents a different risk-adjusted score.
3. Change rate or drawdown bounds. Unnecessarily narrows the finite ratio's domain.

## Decision

Require both inputs to be nonboolean numbers.Real scalars convertible to finite float values.
Validate before the zero-drawdown convention; decline invalid/unrepresentable inputs with
ValueError. Preserve any finite signed annualized return and drawdown magnitude, the absolute
drawdown denominator, and zero for valid zero drawdown. Evaluate the same native quotient;
if its result is nonfinite, raise ValueError instead of publishing it. No arbitrary rate caps,
drawdown floors, sign restrictions, threshold changes or generated-data correction.

## Consequences and limits

Invalid numerators cannot hide behind zero drawdown, and composed metrics cannot publish an
infinite Calmar. RED tests reproduce scalar shortcut and direct/composed overflow failures before
correction. Independent rational ratio oracles protect finite results, sign symmetry and the
valid zero convention; Fraction/numpy real inputs remain float-representable. This ensures finite
publication, not high-precision ratios at extreme finite scales or robust statistical coverage.

## Reversal

Remove scalar and finite-quotient validation. This reopens findings 121 and 123.
