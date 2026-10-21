# ADR-339: Refuse nonfinite latest paper signals before clipping

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Codex autonomous session 12, ISO 2026-W43; independent research review
- **Extends:** ADR-021, ADR-139
- **Preserves:** ADR-120
- **Resolves:** FINDING-287

## Context

`latest_signal` converts the frozen strategy's last weight to float, then applies
Python `min(1, max(-1, weight))`. A NaN compares false inside that expression and
becomes -1. In a controlled finite-price fixture this proceeds through
`quote_position` and equal-weight sizing to a full short target. Positive and
negative infinity similarly become full directional weights. Source quality does
not establish validity of a subsequently computed strategy output. No affected
real catalog output or historical paper order is established.

## Options Considered

1. Require a finite converted last weight before the existing clamp.
   - Pro: small, explicit refusal at the point where undefined output gains direction.
   - Con: a bad signal aborts the whole target calculation and defers reconciliation.
2. Replace invalid weights with zero or skip the symbol.
   - Pro: other names could continue.
   - Con: fabricates an exposure or changes allocation without valid strategy evidence.
3. Enforce a new global PositionQuote schema or strategy-output validator.
   - Pro: could cover additional direct-input and shape contracts.
   - Con: broader policy, including ADR-120's deliberate NaN-price-to-flat behavior.
4. Keep saturation for nonfinite values.
   - Pro: preserves current behavior.
   - Con: retains the reproduced conversion of missing evidence to a full short.

## Decision

Bind the same legacy `float(signals.iloc[-1])` once. Require `math.isfinite` or
raise ValueError, then apply the identical existing finite clamp. Retain finite
out-of-range saturation, fractional conviction, signed zero, accepted legacy
float conversions and native conversion errors. Do not change source validation,
strategy math, price policy, equal-weight arithmetic, broker interfaces or rails.

## Consequences

The existing `compute_targets` call leaves `quote_position` outside its provider
failure handler. Therefore invalid computed weights abort the whole calculation;
main calls reconciliation only after that calculation returns. This defers new
reconciliation orders for the invocation rather than inventing a zero target.
It is not a per-symbol skip policy or rollback of earlier broker reads/orders.
The refusal also bypasses main's later equity-snapshot append; ledger capture
ordering is unchanged. No actual broker operation is part of verification.

Test NaN and both infinities before implementation, then protect valid finite
clipping with Hypothesis and signed/typed compatibility controls. Exercise the
pure orchestration refusal using quality-passed synthetic input and no broker or
provider calls. Independent review confirmed the witness and 57 finite controls.
Require the full backend/frontend gate and exact pushed CI before delivery.

No validation threshold, search/gate fingerprint, accounting v14, frozen cohort,
generated JSON or historical order claim changes. Reversal removes the finite
check and restores the documented defect; use a superseding ADR to change the
failure policy instead of silently manufacturing targets.
