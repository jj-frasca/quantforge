# ADR-204: Refuse native higher-moment underflow

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 13, ISO 2026-W41
- **Resolves:** FINDING-144
- **Extends:** ADR-182, ADR-203, ADR-044

## Context

Finite skew/raw-kurtosis outputs can conceal native fourth-moment underflow.
FINDING-144 shows raw kurtosis 4.66875 becoming 3.0 at a common positive scale
change. Strict caller state instead raises, contradicting nullable-unmeasured
moment policy. Checking output finiteness alone is insufficient.

## Decision

Keep intrinsic source validation and short/exact-constant shortcuts outside the
arithmetic catch. Around the existing native moment calculations, set underflow
to raise while retaining existing overflow/invalid/divide handling. Catch native
FloatingPointError and return None; retain existing nonfinite/zero-dispersion and
nonfinite skew/kurtosis None guards. Underflowing moments cannot become finite PSR
evidence or leak an ambient-state-dependent exception. No observations are
changed, dropped, normalized or counted differently.

Advance accounting identity to
`whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-v9` because
previously finite moment evidence now becomes unmeasured. Historical identities
remain attributable and cannot match this procedure. Replacement rates remain
unmeasured; no calibration dispatch or generated-data edits. All thresholds stay.

## Verification and limits

RED tests cover partial fourth-moment underflow and variance/other-moment
underflow under ignore/warn/raise, with complete signed nullable inputs. An
independent bias-corrected sample-moment oracle protects ordinary native results;
malformed inputs retain ValueError and count remains exact. Historical v8 identity
restoration and current pin protect calibration separation. This is refusal of
unmeasurable native arithmetic, not a scaled higher-moment estimator or a proof
that every remaining finite estimate is accurate. FINDING-145's independent
Sortino representation question remains open.

## Reversal

Restore ambient underflow handling and v8 identity. That reopens FINDING-144.
