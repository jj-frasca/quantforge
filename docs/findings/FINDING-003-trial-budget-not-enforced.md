# FINDING-003: GateConfig's trial budget is inert

- **Severity:** High (methodology contract and compute bound)
- **Status:** Open; deliberately separated from ADR-046
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
