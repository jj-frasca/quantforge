# FINDING-284: Finite native evidence can produce infinite Sharpe standard error

- **Date:** 2026-10-21
- **Status:** Resolved by ADR-336
- **Scope:** sharpe_standard_error returned uncertainty

## Evidence

After original scalar and integral-square validation, direct calls can still
return infinity from finite evidence. Parent and independent deterministic
probes confirm both native square overflow and history-division overflow.

At score zero and the smallest positive Python float history, 2**-1074, the
formula is sqrt(2**1074) = 2**537, exactly representable as a finite float.
The actual native intermediate division overflows and the helper returns inf.
This witness does not depend on NumPy scalar arithmetic or warning policy.

Additional independent controls use exact Fraction representations of the
original operands and a Decimal100 square root:

| Score | History | Native SE | Exact-model control, rounded |
|---|---|---|---|
| np.float16(300) | 1 | inf | 13.40042643244716 |
| np.float32(1e30) | 1 | inf | 4.4543540989004816e28 |
| np.float64(1e200) | 1 | inf | 4.45435403187374e198 |
| 0 | np.float16(2**-24) | inf | 4096 |
| 0 | np.float32(2**-149) | inf | 2.671373890628154e22 |
| 0 | np.float64(2**-1074) | inf | 2**537 |

Every listed mathematical control is finite and binary64 representable. Under
NumPy warn policy the NumPy operations warn and return infinity; under raise
they retain their native FloatingPointError. Existing Python floating square
overflow and huge integer/Fraction arithmetic already raise OverflowError and
are not nonfinite-return witnesses. No zero-SE or finite incorrect floating
estimate is established by these ordinary native probes.

## Meaning and limits

Source validity and integral-square integrity do not certify the returned
uncertainty. Ordinary frontier, category-report and capture producers use
validated float scores and realistic source-derived histories, with additional
checks in the frontier and capture boundaries. No actual production occurrence,
affected graduate, historical rate or changed calibration is established.

The proposed refusal does not recover representable answers or certify finite
precision. Generic intermediate type/sign integrity and custom Real operators
remain separate. Tiny square underflow can be harmless because the numerator
adds one; no strict-positive-square policy is justified here.

## Resolution

ADR-336 retains the native arithmetic, warnings and exceptions, then requires
the returned SE to be finite and positive. Positive uncertainty is a preventive
model contract, not a claim that an ordinary native zero failure was observed.
Parent froze 60 post-ADR335 scalar outcomes and 24 frontier reports, baseline
SHA256 cd7ceb42e8e7232a79af27c9f4de4d7b631d8fa9f1bec58d50ad934ffd50cc5c.
Actual preimplementation TDD recorded 13 failures and 19 controls. Final 223
focused tests pass. Independent research review confirms all 60 scalar outcomes,
24 frontier reports, the prior runtime AST and exact finding controls. Another
54 policy comparisons retain 39 native values/errors and all warnings while
15 formerly infinite results receive the intended refusal. Fresh foreground
make check-all passed 13,614 backend and 566 frontend tests, lint, formatting,
typing and both coverage gates. No threshold, model, fingerprint, v14, generated
record or frozen cohort changes.
