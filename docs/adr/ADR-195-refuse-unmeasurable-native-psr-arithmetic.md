# ADR-195: Refuse unmeasurable native PSR arithmetic

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 13, ISO 2026-W41
- **Resolves:** FINDING-130
- **Extends:** ADR-054, ADR-192, ADR-193

## Context

Original finite scalar validation does not make derived PSR arithmetic finite.
SE overflow can publish 0.5 for a positive standardized excess, while native
exponentiation or count conversion raises OverflowError outside the consumer's
ValueError-to-unmeasured policy. A zero SE from underflow is also unmeasurable.

## Options Considered

1. Refuse undefined native arithmetic with ValueError at the public PSR boundary.
2. Scale/rewrite the formula to recover extreme results. A separate numerical
   implementation needs independent precision evidence and a separate decision.
3. Allow infinity/zero SE to imply an ordinary probability. Invents evidence.

## Decision

Keep accounting/source validation first and the existing strict positive Pearson
moment-slack policy. Require finite native moment slack. Compute the same native
SE-squared expression, requiring a finite positive result before square root.
Convert OverflowError in these expressions to ValueError. Keep the original
Gaussian CDF and its legitimate bounded tail saturation; no finite standardized
score requirement is added. Probability DSR delegates to this same boundary and
whole-search accounting retains its existing ValueError-to-None behavior.

## Consequences and limits

Source-valid but unmeasurable native arithmetic no longer produces a spurious
measured probability or aborts a hunt through OverflowError. Tests fail before
implementation, protect direct/wrapper/consumer propagation, and compare ordinary
finite values to an independent formula. No moment policy, valid formula, gate,
threshold, count, calibration identity or generated record changes. Extreme
mathematically valid inputs may remain unmeasured; this is refusal rather than
numerical recovery and does not claim accuracy for every finite native result.

## Reversal

Remove derived finite/positive checks and native overflow conversion. This reopens
FINDING-130 and its consumer error-channel mismatch.
