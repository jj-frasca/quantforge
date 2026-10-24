# ADR-357: Validate original drawdown equity evidence

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Codex autonomous session 26, ISO 2026-W43
- **Extends:** ADR-110, ADR-182, ADR-186, ADR-356
- **Resolves:** FINDING-297

## Context

The raw max_drawdown primitive accepts incomplete equity: pandas skips missing
observations during reduction. Complex observations lose their imaginary part
at the final float conversion. Empty malformed dtypes return a numeric zero.
Composed engine metrics validate wealth earlier, but the public primitive does
not enforce original source validity. FINDING-297 records direct witnesses.

## Options Considered

1. **Validate dtype and complete native finite observations before empty handling.**
   - Pro: refuses invalid evidence without changing accepted operands or formulas;
     preserves genuinely finite wider floats that cannot project to binary64.
   - Con: previously accepted malformed inputs now raise earlier.
2. **Reuse the return-sample helper's float64 inspection.**
   - Pro: shares validation code.
   - Con: narrows genuinely finite wider equity even when its ratio is measurable.
3. **Drop missing rows or coerce source observations.**
   - Pro: produces more numeric outputs.
   - Con: silently changes the claimed source sample and discards information.

## Decision

At max_drawdown entry require real numeric nonboolean/noncomplex dtype, then
reject equity.isna().any() or nonfinite native Series observations before the
existing empty shortcut. Inspect native Series with np.isfinite without float64
conversion. Retain original operands, cummax, division, subtraction, reduction,
clamp and empty-numeric zero. No output recovery, positivity restriction, calendar
policy, warning-state change or new helper is introduced.

## Consequences

Missing, infinite and nonreal evidence cannot masquerade as a measured drawdown.
Complete nullable numerics and finite wider inputs preserve prior arithmetic.
This validates source evidence only: finite zero/negative equity, degenerate
derived NaN or native exceptions remain under their preexisting behavior.
Sparse numeric cummax remains unsupported; source validation does not promise
arithmetic support for every numeric extension dtype. Downstream invalid derived
equity may now refuse, so universal completion or unchanged-rate claims are not
justified. No production occurrence or affected graduate is established; no
estimator, threshold, policy hash, v14 identity, generated record or frozen
cohort changes. Tests must preserve native compatibility and document limits.

## Reversal

Remove the entry guards. This reopens FINDING-297.
