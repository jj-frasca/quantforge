# FINDING-003: GateConfig's trial budget is inert

- **Severity:** High (methodology contract and compute bound)
- **Status:** Fixed by ADR-048; calibration refreshed 2026-08-20
- **Affected:** ADR-015/016, `GateConfig`, longitudinal and cross-sectional search

## Finding

`GateConfig.trial_budget` is versioned and persisted but no production path reads it. A caller can
evaluate arbitrarily many configurations while the artifact continues to advertise the configured
budget.

The default full-catalog longitudinal search resolves 667 coarse configurations at
`n_per_param=3`, already more than three times the recorded default budget of 200, before optional
refinement. Silently turning the field into a hard exception would therefore break every current
full-catalog hunt and calibration. Silently truncating grids would make strategy ordering select
which hypotheses exist. That allocation policy needs an explicit follow-up decision and a fresh
null/power calibration; it is not folded into the denominator correction in ADR-046.

## Required behavior

Define a deterministic, order-robust allocation policy for the candidate budget, enforce it before
backtesting, fingerprint the resolved budgeted grids, and re-run null and power calibration. Until
then, `trial_budget` must not be described as an enforced cap.

## Resolution

ADR-048 assigns every eligible family a two-config PBO minimum, distributes remaining capacity by
canonical-name water-filling, uses deterministic maximin parameter-space coverage inside oversized
grids, and budgets adaptive refinement as one additional family. Longitudinal and cross-sectional
search will fail before backtesting when the requested budget cannot preserve those minima. The
implementation is green. The cloud sole writers refreshed null calibration at commit `cfabdcb`
and power artifacts in runs 32340042967/32340043401. The resulting zero-power measurements exposed
the separate diagnostic gap recorded in FINDING-005.
