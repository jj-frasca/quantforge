# FINDING-105: Monte Carlo floor overwrites subnormal prices

- **Date:** 2026-10-04
- **Severity:** Medium — raw paths can violate initial-price and zero-volatility identity
- **Status:** Resolved by ADR-173

## Evidence

ADR-123 intends the smallest positive float floor, but `np.finfo(float64).tiny` is the smallest
normal float, about 2.225e-308. The smallest positive subnormal is about 4.94e-324. With s0=1e-320,
mu=0 and sigma=0, every returned value (including the initial column) is overwritten to 2.225e-308.
No drift or genuine underflow justifies that price-scale change.

## Correction and limits

ADR-173 retains positive flooring at the actual smallest positive representable value. Subnormal
inputs and flat paths retain their exact value. The unit-wealth risk estimator's loss statistics
remain unchanged at this scale; no historical report or threshold is rewritten.
