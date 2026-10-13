# ADR-274: Preserve mixed signed/unsigned integer excess differences

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** Codex autonomous session 6, ISO 2026-W42
- **Resolves:** FINDING-223
- **Extends:** ADR-273

## Context

ADR-273 prevents both-unsigned modular wrap. Mixed signed/unsigned integer sources
remain a distinct failure: pandas promotes large operands to float64 before
subtraction. With base=int64max-4 and strategy offsets [0,3,2] versus benchmark
[1,2,4], exact differences [-1,1,-2] become zeros. Both original inputs are
complete nonnegative integer evidence. IR and tracking error falsely report zero.
All 64-bit plain/masked pairings and both directions reproduce lost evidence.

## Options considered

1. Extend exact integer-difference dispatch to original mixed signed/unsigned
   integer families, reusing ADR-273's existing helper and exact encoding checks.
2. Use an observation-size threshold. Adds an arbitrary value-dependent path and
   risks missing original source distinctions; it is unnecessary for family scope.
3. Convert operands first or cast to int64. Either loses large-neighbor differences
   or cannot represent the complete unsigned range.
4. Replace every integer moment/subtraction. Wider decision than this defect needs.

## Decision

After original source guards and alignment, additionally dispatch only when both
sources have native integer np.dtype kind i/u or classic masked Int/UInt8/16/32/64,
and their original kind set is exactly {i,u}. Reuse the unchanged exact Python
integer subtraction-before-native-encoding helper and integer-ratio certification.
Keep its unsigned name/message: these pairs contain an unsigned source, and its
expanded purpose is documented. Unencodable exact differences remain ValueError.

Construct plain native floating excess with original index and public pandas
name consensus. This family-wide policy deliberately changes the derived dtype
for small mixed integer pairs whose old subtraction already worked, and IR/TE
may change when ADR-272's native wider dispersion consumes that representation.
There is no promise of byte-exact complete output for any mixed integer pair.

Both-unsigned ADR-273, signed-only, floating/native-wide and unsupported extension
paths remain exactly as before. Original negative/missing source evidence refuses
before the helper; derived excess <=-1 remains a valid difference. Beta/alpha,
source means/covariance, drawdown and other financial formulas are unchanged.
No threshold, calibration identity, workflow, generated record or schema changes.

## Evidence and limits

Independent scratch review: eight public large-neighbor failures, 512 all8x8
both-direction/four-fixture exact difference cases and 128 original-negative source
refusals. Require public RED before code, exact Python/Fraction/Decimal oracles,
meaningful Hypothesis samples, native capability/max refusal, source/metadata/
overlap/error-state checks and unchanged complete outside-scope baseline results.
Run independent final review, foreground make check-all and exact master CI.

This certifies encoded excess differences only. Original integer means/covariance
and beta, float64 source validation, native moment precision and final scalar
rounding remain separate limitations. No historical contamination or universal
comparator precision/strict-error-state claim is made.

## Reversal

Remove only the mixed-kind dispatch/predicate and its dtype declaration, restoring
original mixed integer subtraction. This reopens FINDING-223 while retaining273.
