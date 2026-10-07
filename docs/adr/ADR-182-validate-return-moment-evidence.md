# ADR-182: Validate return-moment evidence

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 11, ISO 2026-W41
- **Resolves:** FINDING-114 and FINDING-115
- **Extends:** ADR-054, ADR-167

## Context

pandas moment estimators skip missing observations while ReturnMoments.n_returns counts supplied
rows. NaN padding can therefore increase a PSR without adding observed evidence. Complex and
boolean payloads also bypass the numeric domain. Separately, extreme finite observations can
produce nonfinite skew/kurtosis even while their sample standard deviation remains finite.

## Options Considered

1. Validate complete real numeric inputs and decline unmeasurable finite moment arithmetic.
   This preserves the existing estimators and nullable diagnostic semantics.
2. Drop missing rows and count only the remainder. This changes the supplied research sample.
3. Replace extreme moment estimators with scaled arithmetic. A separate numerical-method change
   requiring independent high-precision oracles; not necessary to avoid invalid publication.

## Decision

Before short/constant shortcuts, require real nonboolean numeric dtype and finite supplied values.
Reject missing/object/string/complex/boolean inputs with ValueError; complete nullable numeric
Series remain supported. Do not impose a wealth-preserving >-1 bound on distribution summaries.
Finite histories with fewer than four observations or no measurable variance continue to return None.

Preserve native sample standard deviation, skew and excess-to-raw kurtosis conversion. Locally
handle upper arithmetic warnings, then return None when computed skew or raw kurtosis is nonfinite,
as already done for unmeasurable variance. No missing rows are removed and the count remains the
exact complete supplied sample length. Finite representable calculations are unchanged.

## Consequences and limits

Missing padding cannot increase PSR evidence length. An undefined finite-input moment summary is
explicitly unmeasured rather than a ReturnMoments carrying NaN. This is an intrinsic public-helper
boundary; checked engine search paths already supply complete returns. The live margin gate,
probability formula, thresholds and calibration identity do not change. Other extreme arithmetic
precision and underflow are outside this slice. No generated records or workflows change.

## Reversal

Remove intrinsic input/output validation. This reopens FINDING-114/115.
