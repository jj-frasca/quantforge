# ADR-329: Refuse zero parameter dispersion contradicted by converted evidence

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** Codex autonomous session 6, ISO 2026-W43
- **Extends:** ADR-317/324
- **Resolves:** FINDING-276 for zero native sample STD on unequal converted observations

## Context

Finite distinct Float64 observations [1e-200,2e-200] produce native sample STD 0
because NumPy squares underflow. Exact Fraction-centered sample variance of the
converted binary64 observations is positive. Taking a Decimal square root only
after exact variance yields approximately 7.0710678118654751e-201. Native mean,
STD and CV remain finite, so ADR-324 does not refuse this contradictory zero.
[0,1e-200] and [-1e-200,1e-200] independently confirm the boundary. No production
occurrence, false graduate or calibration impact is established.

The existing 1e-9 denominator regularizer means the positive oracle dispersion
still yields a binary64 stability score rounding to 1. This is a dispersion
evidence correction, not an established gate flip or economic ranking change.

## Decision

Preserve every original input/count/shape check and numerical expression. After
the unchanged native mean/sample STD calculation and existing finite guard,
before CV, add only:

```python
if std == 0 and not np.all(arr == arr[0]):
    raise ValueError("zero stability dispersion requires identical converted observations")
```

This guard checks exact equality in the already converted Float64 array. It
refuses a zero measured STD contradicted by unequal converted observations;
it neither computes a replacement variance nor repairs underflow. Native zero
and signed-zero constants remain accepted. Preserve epsilon 1e-9, sample ddof 1,
mean, extrema, positive fraction, CV, clipping and reciprocal exactly.

Do not set NumPy policy, suppress warnings, catch native exceptions, scale or
recover arithmetic. Under ignore/warn the explicit ValueError follows the native
calculation; warn still emits its native underflow warning. Under raise the
existing FloatingPointError can preempt the guard. Caller policy remains exact.

The rule does not certify original values before Float64 projection, positive
partial-underflow dispersion, finite rounding, or a positive computed variance
on an exactly constant array caused by rounded centering. In particular,
[1e-160,2e-160] has positive native STD and stays outside this correction.
The equal converted-array comparison intentionally treats +0 and -0 as equal.

No dataclass/direct-constructor, report, shared engine, selector, threshold,
accounting-v14, generated record or frozen-cohort change. Historical results
retain their executed attribution; no source or calibration rerun is authorized.

The refusal is conservative: some unequal extreme subnormal arrays have a
positive exact sample STD that cannot round to a positive Float64 value.
The three recorded witnesses have representable positive oracle dispersion;
that is not promised for every future refusal. No numerical recovery is claimed.

## Alternatives and reversal

1. Refuse only zero STD contradicted by converted inequality: chosen narrow boundary.
2. Recover scaled/high-precision dispersion: deferred; changes the estimator.
3. Reject every native underflow warning: too broad; includes positive partial underflow.
4. Keep contradictory zero because the score still rounds to 1: leaves false dispersion evidence.

Reverse by removing the two-line guard and restoring its leading docstring;
retain the written witness and reopen FINDING-276.

## Verification

Decision adopted before tests/source edits; write tests and observe actual RED
before changing runtime. Exercise all three unequal witnesses under ignore/warn,
native raise behavior, unchanged caller policy, exact constants/signed zero,
ordinary controls and positive partial underflow. Use exact Fraction variance
for independent witness/property oracles; do not center in rounded Decimal.
Preserve original validation and nonfinite-reduction precedence. Freeze all 20
ordinary prior cases in a new unique baseline without overwriting old receipts:
/tmp/qf-w43-s6-stability-zero-baseline.json. Require exact accepted payloads and
whole prior AST preservation after deleting only this guard/restoring docstring.
The existing bounded-score property retains its entire input generator and all
successful-result bound, profitable-fraction and mean assertions. Extend its
contract only for this documented refusal, requiring the exact new error,
independent positive Fraction variance and zero native converted STD; do not
filter inputs, skip examples or swallow arbitrary errors. This preserves its
full domain while checking the newly explicit failure outcome.
Independent review, foreground make check-all, explicit-path commit, fresh
fetch/rebase, immediate individual push and exact master CI remain required.
