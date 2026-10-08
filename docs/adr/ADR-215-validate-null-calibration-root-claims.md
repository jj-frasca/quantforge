# ADR-215: Validate null-calibration root claims

- **Status:** Accepted
- **Date:** 2026-10-08
- **Deciders:** Codex autonomous session 17, ISO 2026-W41
- **Resolves:** FINDING-161
- **Extends:** ADR-036, ADR-037, ADR-158, ADR-213

## Context

Leaf validation cannot establish a durable calibration's denominator, counts,
rate or scalar summaries. The root accepts impossible counts and rates, and
an infinite maximum DSR survives authoritative merge reconstruction.

## Decision

Require original nonboolean integral counts: positive searched symbols and
nonnegative graduates/survivors. Require finite real nonboolean root scores,
with a nonnegative deflation bar, an original false-graduation rate in [0,1],
and optional None only for the existing nullable holdout maximum. Check bounds
before float rounding. Signed finite maxima and valid numeric scalars remain.

Require survivors <= graduates <= searched symbols, graduate count equal to
the graduate-list length, and rate exactly equal to graduates/searched symbols.
That is the ratio the producer and merge already compute, without tolerance,
clamping, inferred counts or denominator changes. Reuse the original-value
probability guard for leaf probabilities and the root rate.

Nested/merge reconstruction inherits these contracts. Preserve JSON shapes and
legacy optional-array semantics. No estimator, reference, search/gate threshold,
methodology identity, workflow or generated-data changes.

## Alternatives and limits

Checking only merge leaves standalone/JSON evidence invalid. Correcting supplied
counts or scores silently substitutes a different claim. Permitting an approximate
rate allows a contradictory artifact even though the exact ratio is available.

This does not validate legacy diagnostic arrays, recompute maxima or the
deflation-bar formula, enforce all symbol relationships, or certify downstream
arithmetic. These boundaries need separate reproduced findings.

## Verification

Observe original-value, exact-Fraction, count/list/rate and unchecked-copy merge
failures before implementation. Protect signed/zero scores, numeric scalars,
nullable maxima, legacy absence and a coherent full-graduation rate. Read all
committed null artifacts without writes, review independently and run affected
consumers plus the full foreground repository gate before delivery.

## Reversal

Remove root field validators and count/rate checks; this reopens FINDING-161.
