# ADR-287: Recover Float64 volatility from anchored differences

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** Codex autonomous session 9, ISO 2026-W42
- **Resolves:** FINDING-236
- **Extends:** ADR-208

## Context

Original native/classic Float64 nonconstant returns near 1e-200 lose native
variance. ADR-208's level-normalized recovery erases represented near-equal
spacing, accepting annualized volatility 21.03%, 8.25% or 11.11% high for n=3,4,7.
This is the descriptive BacktestMetrics field, separate from ADR-286's scorer.

## Options considered

1. Anchor represented differences only for finite failed Float64 STD: selected.
2. Replace every native estimate: changes ordinary rounding without demonstrated need.
3. Keep level normalization: preserves the reproduced false risk measurement.

## Decision

For original native Float64/classic nullable Float64 only, use anchored recovery
when the STD call raises underflow and recomputing with underflow ignored yields
finite dispersion, or native STD collapses to finite zero for a validated
nonconstant sample. Detect the STD call separately from annualization. Preserve
ordinary measurable native results, nonfinite STD recovery, annualization-only
failures and all other source families exactly.

Subtract the first original observation, normalize differences by their maximum
magnitude and compute sample STD. Combine difference-scale and normalized-STD
mantissas with sqrt(252), then restore their combined exponent once. Require
positive finite final volatility: ADR-208's final-rounded-zero refusal remains.
Source validation and short/exact-constant conventions precede recovery; caller
observations and floating-point state remain unchanged. No arbitrary risk floor.
O(n) time and memory, no dependency/cache. Normalized differences contain zero
and a unit-magnitude observation; no nearconstant level normalization occurs.

Selected cases use exact represented Fraction variance and agreeing Decimal
200/800 targets. Subnormal control cases permit one output ULP certified against
exact squared midpoints; universal correctly rounded recovery is not claimed.

The field is descriptive only: trial accounting stays v11, current-version
calibration remains unmeasured and historical v10 cohorts retain attribution.
No threshold, selector, grid, budget, schema or generated-record changes.

## Evidence and limits

Independent scratch scope approved twelve public reproductions, 180 exact
nearconstant/mixed-sign oracles, 22 exact subnormal midpoint controls, 306 exact
ordinary/outside/nonfinite baselines and 314 draft/original financial tests.
100k-observation prototype about .003s. Require public RED, provenance/source
controls, Hypothesis, unchanged engine regressions, independent final review,
foreground make check-all and exact pushed CI before completion.
No false graduate or historical market contamination has been established.

## Reversal

Restore ADR-208 recovery; retain the written finding and original historical
attribution. Do not change accounting or relabel prior measurements.
