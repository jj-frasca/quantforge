# FINDING-153: Subnormal log compounding depends on platform error signals

- **Date:** 2026-10-07
- **Severity:** Medium — valid tiny return paths fail on some platforms; master CI red
- **Status:** Resolved by ADR-211; exact repair CI verification required

## Evidence

Exact master CI 37724245662 at e427cd0e fails three unchanged ADR-208 tests:
strict-state annualized-volatility recovery at scale 1e-320 (float64 and nullable
Float64), and the smallest-subnormal two-observation path. All fail earlier in
`_validated_log_returns` at np.log1p with `FloatingPointError: underflow encountered
in log1p`. The macOS full gate passed 3,091 tests; the Linux runner reports
Python 3.12.3. The signal is platform dependent even when the rounded logarithm
remains finite and is a valid tiny return.

Finite returns greater than -1 satisfy the positive-wealth input domain. The
helper validates that domain but leaves log1p underflow controlled by ambient
error state. These subnormal observations need not be rejected; existing final
wealth positivity/finite checks independently enforce the compounding contract.
No inaccurate graduate or changed threshold is asserted.

## Proposed boundary

Ignore underflow only around log1p after original validation. Preserve the native
logarithms, other NumPy error modes, caller-state restoration and every final
wealth check. Add a deterministic platform-signal simulation using actual NumPy
underflow before the real ufunc, plus Decimal800 tiny-log and source-precedence
assertions. Keep all original failing CI cases unchanged.

## Resolution

Eight portable RED cases and five preservation cases precede the correction.
Only validated log1p gets local underflow-ignore; source/wealth checks and all
other policies remain. Tests use an actual NumPy underflow signal before real
log1p, verify Decimal800 subnormal logarithms and caller-state restoration,
and retain all original ADR-208 regressions unchanged. This changes platform
signal handling, not formulas, gate evidence or calibration identity.
