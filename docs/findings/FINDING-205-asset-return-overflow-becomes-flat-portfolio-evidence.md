# FINDING-205: Asset-return overflow becomes flat portfolio evidence

- **Status:** Corrected
- **Date:** 2026-10-11
- **Severity:** High — undefined asset returns disappear into finite portfolio output
- **Scope:** asset_returns and public portfolio aggregation
- **Decision:** ADR-256
- **Prior art:** ADR-254's explicit derived limit; ADR-229/FINDING-179

## Evidence

Independent ordered positive finite prices use A=[float64.tiny,float64.max] and
B=[100,100]. Native A returns are [0,Inf]. An exposed long-A/short-B portfolio
returns [-0.002,Inf]; all-missing signals with zero exposure instead return [0,0].
Multiplication by zero produces NaN, which the portfolio sum skips as though there
were a valid zero return. Ambient ignore and raise error modes both reproduce the
defect in the native pandas kernel.

These are direct synthetic cases, not observed stored records, real cohort results
or measured false graduates. No search, workflow, broker or generated record was
changed. Valid source prices alone cannot establish representable derived returns.

## Correction and verification

ADR-256 keeps native return computation and refuses nonfinite results before
portfolio multiplication, normalizing arithmetic overflow exceptions to ValueError.
Independent pre-code review preserves 16 exact native comparisons including
nullable, uint64, longdouble above float64 range, singleton and empty panels plus
NumPy error state; all 203 engine/forward tests pass under a scratch wrapper.

Before implementation, nine refusal regressions failed and two representable
extreme cases passed. All 255 affected engine/forward/search/IC tests pass after
correction. Independent final review approves 16 exact complete native asset-return
and 64 portfolio-return comparisons across mixed nullable, extreme uint64,
longdouble above float64 range, finite 1e300 ratios, empty/singleton panels, missing
signals and zero/nonzero costs under ignore/raise settings. Caller prices and
NumPy error state remain unchanged. Restoring only the original return expression
reproduces the published whole-module AST. A Hypothesis property refuses constructed
unrepresentable ratios. The full foreground gate passes
5,167 backend and 363 frontend tests, with 97.78% backend and 97.63%
frontend statement coverage; lint and strict typing pass. No scaled fallback, caps, signal/cost/aggregation policy
or threshold changes.
