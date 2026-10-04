# ADR-171: Compute benchmark-relative drawdown in log space

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Codex autonomous session 28
- **Resolves:** FINDING-102
- **Extends:** ADR-112

## Context

The comparator accepts finite returns greater than -1, but divides two independently compounded
wealth paths. Shared growth can overflow both intermediates, producing NaN relative wealth and
silently skipping a later relative loss. The ratio itself can remain economically well defined.

## Options Considered

1. Reject any nonrepresentable standalone wealth path. This unnecessarily rejects a representable
   relative drawdown when common growth cancels.
2. Accumulate log relative growth and compute drawdown against running log peaks. This evaluates
   the existing ratio definition without materializing standalone wealth or exponentiating peaks.
3. Clip either compounded curve. This changes relative returns and cannot preserve evidence.

## Decision

Use `log1p(strategy) - log1p(benchmark)` per period, accumulate from a prepended zero log baseline,
and subtract the running maximum log wealth. Relative drawdown is `expm1(min(log_drawdown))`.
This is algebraically the same positive-wealth ratio drawdown under ADR-112. Large negative log
drawdowns can round to -1, the existing representable complete-loss boundary; common huge growth
does not create intermediate infinity/NaN. No alignment, input domain, other metric, or gate changes.

## Consequences and limits

An offline common-growth prefix followed by strategy -20% / benchmark +20% reports -1/3 rather
than zero. First-period losses and SPY-vs-SPY neutrality remain intact. Moderate paths match a
separately compounded ratio oracle. This is numerical robustness for the public comparator domain,
not evidence of a corrupt committed experiment or a typical market path. Extreme covariance and
other scalar metrics remain outside this narrow correction.

## Reversal

Restore independent compounded wealth division. That reopens FINDING-102.
