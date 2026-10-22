# ADR-344: Refuse native nonfinite history before universe-bar shortcuts

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Codex autonomous session 15, ISO 2026-W43; independent research review
- **Resolves:** FINDING-294
- **Extends:** ADR-018
- **Related:** ADR-292/296/334; FINDING-281

## Context

expected_max_sharpe_under_null(607,+Inf) returns0.0. Its native reciprocal is
zero, so invalid infinite supplied history becomes a valid-looking zero
annotation bar. NaN returnsNaN; -Inf obtains0 through the existing T<=0
shortcut. All three return0 when N<2 short-circuits duration handling.
This is deterministic standalone helper evidence, not an observed affected
graduate, report, experiment or calibration rate.

The helper deliberately returns0 for finite N<2 or finite T<=0. Existing
test_universe explicitly requires(51,0)->0; this decision preserves that policy.
F281 qualifies the bar's Gaussian extreme-value interpretation without changing
its runtime. It is not an exact finite-N expected maximum or a zero-error
guarantee. Current frontier callers already reject nonfinite duration, while
ordinary annotation/calibration callers derive duration from validated bars or
finite-positive calibration histories. Those mitigations do not validate the
public helper's direct evidence boundary.

## Options considered

1. Refuse self-unequal or exact signed-infinite original history with native
   comparisons before existing shortcuts.
   - Pro: refuses NaN/infinity without narrowing genuine finite native-wide
     durations or changing native operands/formulas.
   - Con: comparisons execute before N<2; malformed missing/nonscalar/signaling
     inputs may now fail earlier under their native comparison semantics.
2. Require math.isfinite(T), optionally converting T to float first.
   - Pro: a small standard-library guard with familiar behavior.
   - Con: rejects genuinely finite native float128 beyond binary64 range and
     can overflow on huge negative integers that currently return0.
3. Require positive nonboolean Real history and integral valid N.
   - Pro: broader evidence contract.
   - Con: breaks the selected finite<=0 shortcut, bool/0d compatibility and/or
     N domains; separate decisions would be required.
4. Rely on callers, or retain nonfinite-to-zero behavior.
   - Pro: no shared change.
   - Con: leaves direct invalid history able to produce a measured-looking bar.

## Decision

Before the original N<2 or T<=0 branch, inspect the original duration:

```python
if holdout_years != holdout_years or holdout_years in (math.inf, -math.inf):
    raise ValueError("holdout_years must be finite")
```

Keep every original branch, operand, division, sqrt/log expression and return.
Do not convert history or add dtype/Real/nonboolean/count validation. Keep the
ordinary finite-zero/negative and N<2 shortcuts, including(51,0)->0. Refuse
NaN/infinity even when N<2 would formerly bypass duration handling. Preserve
native finite Float16/32/64/longdouble, finite accepted0d inputs, bool,
Fraction, huge negative Python integers and native-wide finite durations.

For native float128 T=2*float64max, retain the existing positive
1.8880843389847055e-154 bar. For finite native +1e400, retain the existing
derived0; native finite-derived arithmetic underflow/precision is separate.
Negative1e400 and huge negative Python integers retain shortcut0. This is an
original-nonfinite refusal, not certification of finite-derived results.

Retain original native comparison/error semantics. In particular Decimal sNaN,
pd.NA and multi-element ndarray can now fail before a formerly bypassing N<2
branch. Do not normalize their exceptions or claim universal malformed-input
error equivalence. Finite positive Decimal still reaches its original float/
Decimal division TypeError; ordinary finite strings/complex retain their prior
native path. No new support or ban is adopted for arbitrary custom types.

## Consequences and verification

Only the declared native nonfinite evidence boundary is added. Actual protected
production occurrence, false graduate or changed rate is not established.
Errors now refuse direct invalid evidence; caller outcomes depend on their own
validation/error handling. No unchanged-rate claim follows from preserved
finite formulas or fingerprints. Do not replay, repair or relabel frozen cohorts.

Preserve the original annotation model/thresholds, N geometry, finite formula,
gate configuration and intended search/accounting-v14 identity; verify current
fingerprints explicitly. Edited source provenance changes. Original ADR018 and
historical measurements remain untouched. Do not conflate this annotation
with per-symbol graduation or claim the model eliminates selection luck.

Scratch audit covers47 original histories across N0/1/607, including native
floating widths,0d nonfinite controls, finite-wide/huge-int compatibility and
existing native errors. It executes only direct deterministic helper calls.
This is not repository TDD or a full verification gate.

Observe meaningful repository RED before runtime edits for all three nonfinite
values across the original shortcuts, then protect finite-zero/negative/N<2,
bool/Fraction/0d/wide controls and existing N behavior. Compare complete old/new
runtime AST except the exact native guard and declared explanatory docstring;
preserve every old test. Require independent final review, foreground
make check-all and exact pushed CI. No new source law or calibration is needed.

## Reversal

Remove the exact native-history guard. This restores F294's nonfinite-to-zero
and NaN publication behavior. Any stricter positive-history, original scalar
type, N-domain or finite-derived arithmetic policy needs a separate decision.
