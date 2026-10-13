# ADR-271: Preserve excess returns for native wider and masked numeric pairs

- **Status:** Accepted
- **Date:** 2026-10-12
- **Deciders:** Codex autonomous session 4, ISO 2026-W42
- **Resolves:** FINDING-220
- **Extends:** ADR-179, ADR-270

## Context

Original aligned native wider floating returns paired with classic pandas masked
Float32/Float64 or integer returns pass the numeric source contract, then fail at
excess=strategy-benchmark with KeyError for float128. Installed pandas constructs
an unsupported wider FloatingArray representation before beta can be computed.
This separate compatibility failure was disclosed during ADR-270's TDD review.

## Options considered

1. Construct a plain native wider excess Series for these bounded mixed pairs.
   Retains original values, supported source contract and downstream formulas.
2. Convert every pair to arrays. Unnecessarily changes ordinary nullable outputs.
3. Cast the wider source to float64. Erases the distinctions ADR-270 just repaired.
4. Catch the KeyError and decline the comparison. Fails softly but discards valid
   complete observations when their difference is natively representable.

## Decision

After existing source/alignment/finite/positive-wealth checks, dispatch only for a
native floating NumPy dtype wider than float64 paired with a classic pandas masked
numeric dtype: Float32/Float64 and Int/UInt8/16/32/64. Subtract both original aligned
arrays promoted to np.longdouble and construct a plain native wider excess Series
with the original aligned index. Keep original pandas subtraction for every other
pair. No source observation is filled, clipped, dropped or mutated.

Preserve pandas binary result-name semantics through empty ordinary float Series
subtraction containing only the original names. This public metadata operation
handles matching NaN/pd.NA names without a private pandas dependency or a naive
name-equality test. Original source labels and names remain unchanged.

All source guards, exact constant handling, matched wider beta, ordinary paths and
remaining comparator formulas stay. The new mixed-pair excess dtype is explicitly
plain native wider; the previous representation failed rather than producing a
valid output. No gate threshold, calibration identity, workflow, generated record
or persistence-shape change. Arrow/Sparse/third-party extensions are outside this
bounded support claim and retain their prior paths.

## Evidence and limits

Independent scratch prototype passes 200 complete mixed cases across ten masked
numeric dtypes, both sides, five name pairs and complete/partial overlap. Eighty
ordinary/nullable nonwide complete outputs remain exact. Native excess/source
Fraction beta, metadata/index/caller state, constants and missing-value guards pass.

Observe RED before production for the supported mixed pairs; test exact represented
dyadic differences, names including NaN/NA/integer/tuple, aligned-missing refusal,
unaligned missing/partial overlap, source ownership and Hypothesis covariance oracles.
Run independent review, foreground make check-all and exact master CI.

This repairs a representation failure, not universal wider arithmetic precision.
Original downstream mean/dispersion/IR/alpha/tracking/log wealth can still narrow
or lose evidence. ADR-270's needed-moment refusal, source validation's float64
arrays and other numerical limits remain. No promise that every finite mathematical
comparison becomes measurable or that already-rounded source values are recovered.

## Reversal

Remove the bounded mixed-pair subtraction branch and restore original pandas
subtraction. That reopens FINDING-220 without changing source domains or thresholds.
