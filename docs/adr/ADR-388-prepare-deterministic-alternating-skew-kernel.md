# ADR-388: Prepare a deterministic alternating-skew price kernel

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Codex autonomous session8, ISO2026-W44
- **Extends:** ADR-036's constructed-null methodology; preparation only

## Context

A constant ideal conditional return variance with alternating conditional skew is
a distinct stress question from existing frozen null laws. The prior session7
scratch protocol was never adopted, its execution window expired, and it remains
deferred unchanged. No original sources were drawn for this proposal. Independent
data/research reviews recommend proving deterministic construction before any
future execution identity, archive, runner, auditor or schedule is considered.

## Decision

Add only alternating_skew_prices(codes: Sequence[int]) -> NDArray[np.float64] in
research/lab/alternating_null.py. Fix the initial price at128, with at most7399
transition codes. Runtime input must be collections.abc.Sequence, excluding
str/bytes/bytearray; ndarray, mapping, set and generators are unsupported. A future
NumPy caller must explicitly materialize a supported sequence. Empty input yields
one price128. Check maximum count first; snapshot once, validate original elements
as nonboolean Integral in{0,1,2}, then normalize to private Python integers before
recurrence. Invalid containers/counts/elements raise ValueError naming codes. Do
not coerce float codes, flatten arrays, clip, filter, repair or emit partial output.
Arbitrary adversarial Sequence implementations are outside the concurrency policy.

One-based odd transitions use factor65/64 for code0, otherwise127/128. Even
transitions use63/64 for code0, otherwise129/128. Starting at Python float128.0,
multiply once per transition, rounding at each step, and return a fresh contiguous
one-dimensional native float64 array of n+1 prices. No paired products, cumprod,
logs, cumulative exact rational state, final-only rounding or configurable scale.
Output can be mutable; there is no retained state or source-archive identity.

Under ideal independent uniform categories, a=1/128 gives returns(2a,-a,-a) on
odd steps and(-2a,a,a) on even steps. Both conditional means are0 and variances
1/8192; third moments alternate +/-1/1048576. A bounded predictable position has
zero ideal expected gross simple-return P&L; nonnegative turnover costs cannot
create it. This is not zero log drift, an empirical sample property, a PRNG
independence proof, or a broad market/null-calibration guarantee.

Under correctly rounded normal binary64 operations, all allowed native prefixes
remain strictly2^-226<P<2^240, including multiplication rounding u=2^-53. The
native ratio then lies within Sterbenz's exact-subtraction range; its conditional
simple-return mean differs from ideal zero by at most2u+u². This is an absolute,
operation-specific bound, not an exact numerical martingale or engine-wide bias
certificate. Independent exact-Fraction moment and prefix/rounding proofs precede
implementation. Finite source prices do not certify downstream indicator evidence.

No RNG, calendar, OHLCV assembly, source preparation, artifact schema, cohort
identity, deadline, runner, calibration, gate, cost, threshold, generated-data or
accounting-v14 change. This ADR does not authorize an original cohort. Every old
completed/incomplete/expired cohort, timing root and draft identity stays frozen.
Any later first execution requires its own prospective reviewed protocol and all
controlled tooling, independent audits, full gates, publication and exact CI before
draws. Kernel readiness supplies no completion-time feasibility claim.

## Options considered

1. **Pure bounded deterministic kernel (chosen).** Independently testable without
   consuming source draws or entangling orchestration with numerical construction.
2. **Adopt a full cohort now.** Deferred: persistence, observer, independent source
   and final auditors, identity and timing readiness are not yet established.
3. **Vectorized or exact cumulative product.** Rejected: changes the sequential
   finite-arithmetic law under review.
4. **Generic base/amplitude/container API.** Deferred: broadens the proof domain
   without improving this preparation slice.

## Verification and reversal

Observe a genuine missing-implementation RED before adding the function. Verify
exact short examples, parity/categories, empty and7399/7400 boundaries, unsupported
containers/scalars, all-element validation, normalized snapshot, unchanged input,
fresh outputs, Hypothesis prefix/determinism and per-step Fraction rounding oracles.
Use controlled arrays only, never original cohort seeds/RNG draws. Independent
full-horizon/moment/rounding checks and final reviews precede foreground full gates,
individual publication and exact CI. There is no methodology defect finding: this
adds unused preparation machinery and corrects no existing measured result.

Remove the module/tests to reverse tooling adoption; preserve this decision record
and frozen historical artifacts. No production caller or generated evidence depends
on this kernel at adoption.
