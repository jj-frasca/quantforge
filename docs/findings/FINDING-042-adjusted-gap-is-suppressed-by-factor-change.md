# FINDING-042: Adjusted price gap is suppressed by factor change

- **Severity:** High
- **Status:** Resolved by ADR-114
- **Found:** 2026-09-23, Codex autonomous session 9
- **Affects:** `DataQualityEngine` corporate-action classification

## Finding

ADR-113 suppresses `corporate_action` whenever the cumulative adjustment-factor ratio is outside
the split-consistency band. That treats the factor change as an explanation for the close move,
but canonical `PriceBar.close` has already had that factor applied by `OHLCVNormalizer`. A large
move that remains in the adjusted close is therefore not explained by the factor change.

For example, a split can change `adj_factor` while the security also suffers a greater-than-50%
economic or vendor discontinuity. The current implementation emits only
`split_dividend_consistency` and hides the separately documented adjusted-price discontinuity.
The two observations are independent evidence after normalization and must not be partitioned.

## Required correction

Evaluate `corporate_action` from consecutive adjusted closes regardless of `adj_factor`; continue
to emit `split_dividend_consistency` independently when its own factor condition fires. Add a
regression for a simultaneous factor jump and adjusted-close gap. Preserve warning severity,
thresholds, and the honest "flags potential" wording.
