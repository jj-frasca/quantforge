# ADR-256: Refuse nonfinite native cross-sectional asset returns

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 35, ISO 2026-W41
- **Resolves:** FINDING-205
- **Extends:** ADR-024, ADR-229, ADR-254

## Context

Finite positive prices do not guarantee representable native return ratios.
asset_returns can publish infinity from a tiny-to-huge transition. Zero exposure
then multiplies infinity by zero; portfolio aggregation skips that undefined value
and publishes a finite flat result. ADR-254 explicitly left this derived boundary
separate from original source validation.

## Options Considered

1. Refuse nonfinite native asset-return results before portfolio arithmetic.
   - Pro: prevents undefined returns from becoming finite aggregation evidence.
   - Con: refuses mathematically defined ratios beyond the native representation.
2. Scale, cap or reconstruct the return estimator.
   - Pro: might recover more extreme mathematical cases.
   - Con: changes arithmetic, requires separate independent estimator evidence.
3. Trust final portfolio or score validation.
   - Pro: no extra asset-level check.
   - Con: zero exposure can already erase undefined evidence before those boundaries.

## Decision

Compute the original prices.pct_change().fillna(0.0) unchanged. Normalize native
OverflowError/FloatingPointError to ValueError, then require every populated native
return observation to be finite before returning it. Inspect native values without
float64 conversion; preserve zero-cell panels and the defined first-period zero.
Do not change NumPy's error state, scale/cap/fill/drop prices, add a return cap or
replace the estimator. Preserve native finite, nullable and wider-precision outputs.

## Consequences and reversal

An undefined ratio cannot disappear through zero weighting and missing-value
aggregation. Existing valid arithmetic, signals, ranking, costs, source contracts,
schema, thresholds and generated records remain unchanged. The boundary pays one
finiteness check. Remove the result guard/exception normalization and restore the
direct native return expression to reverse this correction and reopen FINDING-205.
