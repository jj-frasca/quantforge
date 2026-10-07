# ADR-194: Validate margin DSR source and finite difference

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 11, ISO 2026-W41
- **Resolves:** FINDING-129
- **Extends:** ADR-046, ADR-190, ADR-191, ADR-192

## Context

Shared accounting guards do not validate the margin-form observed Sharpe. Boolean, nonfinite and
complex scores pass through valid N=1 accounting. Finite observed score and finite haircut can
also overflow their subtraction. Downstream finite-field models protect normal persistence, but
the public statistic should not emit malformed or nonfinite evidence. Direct production callers
supply finite real engine/validated scores.

## Options Considered

1. Validate observed source after shared accounting, then decline nonfinite native differences.
2. Rely only on downstream model fields. Leaves direct users and new consumers unprotected.
3. Cap extreme scores or margins. Changes multiplicity pricing or published performance.

## Decision

Compute the shared nonnegative haircut first, preserving accounting-validation precedence.
Then require observed_sr to be a finite float-representable nonboolean numbers.Real scalar,
normalized to float. Compute the same native subtraction; if the result is nonfinite, raise
ValueError instead of publishing it. Keep signed finite scores, valid N=1 observed-score identity,
count/dispersion contracts, quantiles, haircut clamp and all thresholds/calibration identity.
No arbitrary score caps or formula redesign.

## Consequences and limits

Malformed observed scores cannot become margins, and finite subtraction overflow is unmeasurable.
RED tests precede correction and protect count/dispersion-before-score errors, one/many-trial
source validity, direct finite overflow and independent finite subtraction/signed scalar oracles.
Existing margin<=observed/more-trial properties continue to hold. Python/numpy/Fraction real
sources retain float-kernel compatibility. This ensures finite publication, not high precision of
near-cancelling score/haircut differences. No generated records, workflows or paid services change.

## Reversal

Remove observed-source and finite-difference checks. This reopens FINDING-129.
