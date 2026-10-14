# ADR-285: Preserve exact OLS coefficients for mixed narrow/Float64 sources

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** Codex autonomous session 9, ISO 2026-W42
- **Resolves:** FINDING-234, remaining mixed-floating coverage of FINDING-232
- **Extends:** ADR-283, ADR-284

## Context

Original nativefloat16/32 orclassicFloat32 paired with native/classicFloat64
remains outside the exact coupled coefficient domain. For four represented
Float16 observations near2**10 and a Float64 counterpart offset by half a
Float16 ULP (.5), public annualalpha252.0000000000573 or0 replaces exact126.
At Float32base2**60 and halfULPoffset, publicalpha64512 or34634616274944
replaces exact17317308137472. A coupled slope case publishes447392426.6666666
instead of536870912. An alpha-only repair would retain a known false slope.
Earlier Float16base2**14 was declined rather than publishing false evidence;
that unrelated narrowmean overflow example is explicitly not this finding.

## Options considered

1. Extend the existing exact coupled helper to only these original mixed floating
   pairs. No coefficient arithmetic change; deliberately changes rounding for
   every admitted pair and incurs the bounded exact-sum cost.
2. Exact alpha alone. Smaller change but leaves demonstrated false beta and
   cannot justify accurate source coefficient decomposition.
3. Promote native means. Avoids narrow mean rounding, but still amplifies rounded
   beta and cannot fix large-origin Float64 denominator centering.
4. Dispatch every original real numeric source to the helper. Simpler broad rule,
   unnecessary changes to both-narrow, integer/narrow, wider and third-party paths.

## Decision

Additionally admit one original nativefloat16/float32 orclassicFloat32 source
paired with one original nativefloat64/classicFloat64. Keep the ADR-283/284
common-grid ratio adapter, sufficient sums, constant convention and final
rounding/refusal arithmetic unchanged. Select only original aligned dtypes.

Express the combined exact-helper domain as at least one original Float64 source
AND both sources supported original native/classic integer or native floating
width16/32/64 orclassicFloat32/64. This retains both-Float64 and integer/Float64
predecessors while excluding both-narrow, both-integer, integer/narrow, genuine
wider, Arrow/Sparse and other third-party sources. Both-integer/narrow-only
coefficient estimators remain their existing separate accepted paths.

Final unrepresentable coefficients remain ValueError; legitimate zero/subnormal
rounding remains valid. Original guards, alignment, excess/IR/TE/drawdown,
metadata and caller state remain. Existing source width bounds fit the Float64
common-grid bound, with no intermediate means, floating coefficients, new
production Fraction objects, mutable cache or object Series. No threshold,
calibration identity, generated record, schema, workflow or source policy change.

## Evidence and limits

Independent read-only prototype: seven literal accepted failures reproduced;
408public centeredFraction coefficients with exact noncoefficient/state baseline
outputs,90finite helper pairs/sixoverflow refusals,472complete outside-family
baselines;100kFloat32/Float64 .26s. Existing Float64 encoded2098bit and conservative
~6600bit intermediate bounds dominate narrow values. O(n) streaming time/O(1)
accumulator count remain. Scratch132tests passed before adoption with repoRuff.

Require genuine public RED, original halfULP and coupled coefficient fixtures,
centeredFraction/Hypothesis, constant/source guards/alignment/ownership/state,
full-width/tiny/finaloverflow/zero-subnormal helper controls, predecessor and
outside-family exact preservation, independent final review, foreground
make check-all and exact master CI. Float16 public positive fixtures use2**10
and n<=7 to avoid unrelated native sum overflow; extreme helper-only cases do
not imply universal whole-comparator availability. Already-rounded mixed excess
and other-statistic precision remain separate. Family-wide coefficient rounding
changes intentionally; no historical market contamination is established.

## Reversal

Restore ADR-284's original eligibility predicate, leaving the exact helper and
predecessor coefficient arithmetic unchanged. This reopens FINDING-234.
