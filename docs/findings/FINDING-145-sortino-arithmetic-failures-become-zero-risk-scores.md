# FINDING-145: Sortino arithmetic failures become zero risk scores

- **Date:** 2026-10-07
- **Severity:** Medium — descriptive downside-risk claims can conceal arithmetic failure
- **Status:** Resolved by ADR-205

## Evidence

Sortino for `[-.01, .02, -.03, .04]` is approximately 5.01996016. Scaling every
observation by `1e200` or `1e-200` yields 0.0, although the ratio is unchanged
mathematically. Native downside squares overflow/underflow; the fallback assigns
the same zero used for no downside. Returns `[-1e308, -1.5e308]` with target
`1e308` also produce zero after excess subtraction overflows. Strict error state
can raise FloatingPointError instead. For `[-nextafter(0,1), 1.]`, the true ratio
exceeds float64 range but again appears as zero, so recovery alone cannot fully
solve the public representation policy.

Sortino is descriptive only (ADR-107), not a gate, PBO, DSR or selector input.
This does not change the validity of existing calibration measurements. It is a
direct numerical reproduction, not a production false graduate.

## Next decision

Use native-first recovery for representable scores and choose an explicit
unmeasured representation for truly unrepresentable scores rather than invented
zero. Engine financial properties include tiny transaction costs; blanket failure
would reject otherwise valid wealth/return calculations. Review nullable metric,
API and frontend propagation together if selecting None. Retain full-sample
downside definition, source/target precedence, no-downside convention and fixed
thresholds. No correction is claimed in ADR-204.

## Resolution and limits

ADR-205 preserves native measurable scores and uses two cancelling scales for failed
native arithmetic. Truly unrepresentable ratios are None through the required nullable
metric/API/frontend contract. Measured no-downside zero remains distinct. Against HEAD's
pre-correction function injected from a scratch module, 14 numerical regressions fail
and eight preservation/wire cases pass; corrected focused metric/engine tests pass.
No thresholds or calibration identity changed. General finite-result cancellation
is separately recorded open in FINDING-146; this correction does not claim to resolve it.
