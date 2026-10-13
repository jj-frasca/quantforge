# ADR-273: Preserve exact signed differences for unsigned return pairs

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** Codex autonomous session 6, ISO 2026-W42
- **Resolves:** FINDING-222
- **Extends:** ADR-179, ADR-271, ADR-272

## Context

Both plain and classic masked unsigned sources pass the comparator's real numeric
contract. Pandas subtracts them in unsigned arithmetic, so [0,3,2]-[1,2,4] becomes
[255,1,254] for uint8 instead of [-1,1,-2]. Information ratio changes from about
-6.928 to +18.439. All eight unsigned dtype families and mixed pairings reproduce
modular wrap. Finite checks cannot establish that these differences are truthful.

## Options considered

1. Exact Python integer differences before certified native floating encoding,
   only when both original aligned sources are unsigned integer families.
2. Convert operands to native floats first. On 53-bit platforms maxuint64 and its
   neighbor collapse together although their difference one is representable.
3. Cast to signed int64. Cannot represent the complete uint64 difference range.
4. Promote all integer pairs or silently accept rounded differences. Broadens
   compatibility changes or discards exact evidence; neither is justified here.

## Decision

Dispatch only when both original aligned sources are native unsigned np.dtype or
classic pandas UInt8/16/32/64. Subtract their original scalars as Python integers
before any floating conversion. Encode those exact differences in np.longdouble
and certify each encoded scalar's as_integer_ratio equals (exact_difference,1).
If any cannot be represented exactly, raise ValueError; do not wrap, clip, fill,
round silently or fall back. Construct a plain native floating excess Series with
original aligned index and pandas public empty-operand name consensus.

Keep every other subtraction path, input guard, beta/alpha and drawdown operation.
IR and tracking error consume corrected signed excess through ADR-272's exact
constant/native wider dispersion path. Derived excess may be <=-1; it is a
return difference, not a positive-wealth source return. Its dtype deliberately
changes from unsigned to plain signed floating. No threshold, calibration
identity, workflow, generated record or persistence schema changes.

The ADR-272 plain/masked unsigned maximum controls must reflect exact-encoding
refusal on platforms lacking sufficient native precision. Keep their assertions
when representable and keep the separate native floating represented-constant
control intact. No test is deleted or skipped and no tolerance is loosened.

## Evidence and limits

Independent before-code prototype: 256 all8x8 pairing/fixture probes with Python
integer differences and Fraction/Decimal IR/TE; native and constrained 53-bit
large-neighbor difference one survives; +/-maxuint64 refuses constrained encoding.
Observe RED before code, including all pairings, property tests, metadata, partial
overlap, missing refusal, source ownership and caller state. Independently compare
complete ordinary and existing native-wide outputs, run foreground make check-all
and verify exact master CI before delivery.

This certifies the encoded differences only. Original large integer source means,
covariance/beta, mixed signed/unsigned precision, validation's float64 arrays,
native moments and final scalar rounding retain separate limitations. Historical
market contamination is not established. This is no universal comparator
precision or strict-error-state guarantee.

## Reversal

Remove the both-unsigned dispatch/helper and restore the prior unsigned controls.
This reopens FINDING-222 without changing thresholds or generated evidence.
