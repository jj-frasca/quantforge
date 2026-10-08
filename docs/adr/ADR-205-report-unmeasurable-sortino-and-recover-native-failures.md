# ADR-205: Report unmeasurable Sortino and recover native failures

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 13, ISO 2026-W41
- **Resolves:** FINDING-145
- **Supersedes in part:** ADR-187's native nonfinite-deviation zero fallback
- **Extends:** ADR-107, ADR-203

## Context

Sortino's native arithmetic failures become the same zero used for no downside
(FINDING-145). Some ratios can be recovered, while others exceed float64 range.
Rejecting a whole otherwise valid engine result for an unrepresentable descriptive
metric would violate the existing financial return/cost domains.

## Decision

Keep target/source validation precedence and singleton zero. Determine no downside
from the original observations relative to target, not failed arithmetic; retain
its explicit zero. Preserve every measurable native full-sample downside score.
Otherwise normalize returns and target together by a common positive maxabs scale
before subtraction. Normalize resulting negative shortfalls again before squaring;
divide the normalized mean-excess score by this second scale instead of forming
an underflowing denominator. Both scales cancel mathematically. Keep full-sample
counts and the original annualization and mean-excess definitions.

If normalized arithmetic or the final quotient remains unrepresentable, return
None. Make Sortino a required nullable metric in BacktestMetrics, its API view and
frontend schema. Both result and comparison displays render null as "Not measurable"
and measured zero as 0.00. Legacy numeric values remain supported; missing keys
and nonfinite numeric values remain invalid. Wealth and other measured metrics can
still be returned when this descriptive score is absent.

## Verification and identity

RED Decimal exact-float oracles cover positive scaling, excess subtraction overflow,
asymmetric tiny downside and true ratio overflow. Wire/render tests distinguish
null from zero. Retain all engine cost/sign property domains; strengthen Sortino's
full-domain property so a null within its bounded sample domain must be justified
by the independent Decimal ratio exceeding float64 range. No input filtering,
score capping or risk threshold changes.

Sortino remains descriptive only: no gate, PBO, DSR or selector consumes it.
Calibration accounting identity stays v9 and existing artifacts are unchanged by
this correction. No data edits, paid services or workflow dispatch. Numerical
finite-result precision and general cancellation remain separate limitations.

## Reversal

Restore numeric-only Sortino and the native zero fallback, including API/frontend
types. That reopens FINDING-145 and conceals unmeasured risk as zero.
