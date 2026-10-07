# FINDING-112: Benchmark moments publish nonfinite statistics

- **Date:** 2026-10-07
- **Severity:** High — malformed performance claims escape the finite-input boundary
- **Status:** Resolved by ADR-180

## Evidence

Identical strategy and benchmark return Series `[1e200, 2e200, 3e200]` satisfy the comparator's
finite real positive-wealth input domain but publish NaN beta and alpha. Intermediate sample
variance/covariance overflow; NaN reaches the result while relative drawdown and tracking error
are zero. Identical `[1e308, 1e308, 1e308]` also overflows moment arithmetic and publishes NaNs.
Under `np.errstate(all='raise')` these cases raise FloatingPointError rather than the documented
ValueError; the optional HTTP benchmark comparison does not catch that arithmetic exception.
Independent research-expert probes confirm both normal and strict-mode behavior.

## Correction and limits

ADR-180 keeps the same estimators, locally handles upper arithmetic errors and requires all
published scalar outputs to be finite. Undefined outputs raise ValueError instead of being
published or replaced with zero. Ordinary representable results and constant-benchmark semantics
remain unchanged. This can decline mathematically representable extreme results whose existing
intermediates overflow; stable estimation is a separate possible extension. Tiny-variance loss of
precision is FINDING-113, not repaired by finiteness validation. No generated data or thresholds
changed; these are direct synthetic reproductions rather than claims about committed experiments.
