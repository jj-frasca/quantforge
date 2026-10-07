# ADR-187: Validate Sortino source and target

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 11, ISO 2026-W41
- **Resolves:** FINDING-120
- **Extends:** ADR-107, ADR-185

## Context

Invalid Sortino source evidence and nonfinite target rates can return the ordinary zero convention.
Missing returns contaminate downside deviation; its nonfinite shortcut returns zero. Invalid
singleton evidence bypasses arithmetic entirely. NaN and infinite targets also return zero.
The sole production caller supplies engine returns with default target zero; no intended invalid
contract was found. ADR-107's convention is for valid short or no-downside samples.

## Options Considered

1. Validate target and original source before history/downside shortcuts.
2. Drop/fill missing observations or replace invalid targets. Invents evidence or risk assumptions.
3. Validate only the composed caller. Leaves the public primitive's contract inconsistent.

## Decision

First require a nonboolean numbers.Real target convertible to a finite float; normalize it to the
float64 arithmetic kernel's scalar representation. Reject invalid or unrepresentable targets with
ValueError, including on empty histories. Then reuse _validate_complete_return_sample before the
length shortcut. Accept complete nullable numeric and signed returns, including <=-1, and all
finite representable signed targets; impose no target-rate bounds.

Preserve sqrt(252) annualization, mean excess numerator, full-sample downside-square denominator,
short/no-downside zero convention and existing native nonfinite-deviation fallback. Source rows
are neither filled nor dropped. No thresholds, response schema or generated records change.

## Consequences and limits

Malformed evidence cannot be reported as ordinary absent downside; invalid targets fail with
consistent precedence. Tests first reproduce malformed short/missing/dtype samples and nonfinite
targets, then protect valid nullable/signed data and nonzero target behavior with a direct
sum-of-negative-excess-squares oracle. Fraction and numpy/Python real targets remain supported
through float representation. Extreme finite arithmetic/underflow remains a separate numerical
limitation, not a source-validity claim.

## Reversal

Remove source/target checks and scalar normalization. This reopens FINDING-120.
