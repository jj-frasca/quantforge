# ADR-272: Measure exact constants and native wider excess dispersion

- **Status:** Accepted
- **Date:** 2026-10-12
- **Deciders:** Codex autonomous session 4, ISO 2026-W42
- **Resolves:** FINDING-221
- **Extends:** ADR-179, ADR-270, ADR-271

## Context

Installed pandas variance reduces wider values using float64 moments. Three
longdouble neighbors of .1 have sample dispersion 6.776263578034403e-21, yet
pandas reports 1.8117141909820796e-17. Exactly constant .1 excess can also receive
nonzero dispersion for ordinary and wider floats. Casting a constant maximum
uint64 excess to longdouble fabricates dispersion 1.224744871391589. This must
be corrected before a separate unsigned excess representation repair.

## Options considered

1. Exact constant detection globally, native anchored dispersion for wider
   nonconstant excess only. Preserves ordinary nonconstant arithmetic.
2. Replace every moment estimator. Unnecessary broad compatibility change.
3. Narrow wider excess. Erases valid original distinctions.
4. Correct only the mean. Wrong mechanism: installed floating nanmean already
   retains native dtype; the reviewed mean-cancellation hypothesis was dismissed.

## Decision

Detect exact constancy on the original aligned excess Series, without tolerance.
Use zero sample dispersion for these constants and the existing zero-dispersion
IR/tracking-error convention. This deliberately fixes ordinary constant centering
residuals too; ordinary nonconstant outputs retain their existing path exactly.

For nonconstant excess with a genuine native floating dtype wider than float64,
subtract its first original value, center the translated native array, compute
the native sum of squared deviations divided by n-1, then take its native square
root. Require positive finite variance; needed native underflow raises ValueError.
Keep dispersion native through the existing IR quotient and tracking-error
annualization, converting only final statistics to float. No narrowed fallback,
epsilon, clipping, source repair or threshold/calibration/generated-data change.

Original excess, mean, beta, alpha, relative drawdown, source guards and metadata
remain. Arithmetic can still lose precision or refuse mathematical finite results;
this is not universal numerical certification. A final float tracking error may
legitimately round to zero while a native measurable dispersion gives nonzero IR.

## Evidence and reversal

Independent pre-code prototype: 224 Fraction variance/Decimal IR and tracking-error
oracles; 25 exact constant dtype controls; 80 complete ordinary/nullable
nonconstant comparisons unchanged. Tests must observe genuine RED before code,
including near constants, ordinary constants, strict state, ownership/alignment,
tiny native dispersion, needed underflow, masked/wider compatibility and properties.
Run independent review, full foreground gate and exact master CI before delivery.

Revert the exact constant/anchored dispersion dispatch and helper to restore the
original pandas sample std. That reopens FINDING-221 without changing thresholds.
