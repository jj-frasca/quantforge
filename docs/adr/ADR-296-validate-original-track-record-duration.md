# ADR-296: Validate original available track-record duration

- **Status:** Accepted
- **Date:** 2026-10-16
- **Deciders:** Codex autonomous session 21, ISO 2026-W42
- **Resolves:** FINDING-250
- **Extends:** ADR-015/016/160/295

## Context

GraduationGate compares caller-supplied track_record_years directly with the
MinTRL requirement. A synthetic otherwise-passing report with observed Sharpe1
and100 trials requires9.210340371976184 years. Supplying positive infinity passes
the entire gate. Boolean and zero-dimensional array durations also reach the
comparison as measured history. No actual production false graduate, corrupt
pool record or calibration-rate change is established.

Available history must be a measured finite nonnegative duration. This is distinct
from the required duration: ADR-015 deliberately returns infinity for a nonpositive
Sharpe, and ADR-160 permits that requirement in GateResult.

## Options considered

1. Validate original duration at the evaluator boundary: closes direct-call
   ambiguity without changing the estimator; adds an explicit input refusal.
2. Rely on source-derived history in search: avoids a new check but leaves the
   public deterministic gate accepting impossible evidence.
3. Clip infinity or coerce booleans/arrays: keeps permissive callers but invents
   measured history. Rejected.

## Decision

After existing report reconstruction and minbtl_years evaluation, require original
track_record_years to be a nonboolean numbers.Real scalar, finite and representable
as a Python float, and nonnegative on its original value. Reject invalid evidence
with ValueError naming track_record_years before evaluating any other predicates.
Inspect float conversion only for finiteness; retain the original operand for
range and MinTRL comparisons, so exact negative Fractions rounding to minus zero
are refused and valid comparisons retain their numeric semantics. Accept zero,
finite signed zero and supported NumPy/Fraction real scalars. No upper cap.

Keep MinTRL formula, count precedence, threshold values, GateConfig hash, all valid
native comparisons and reason text unchanged. Required positive infinity remains
valid; finite available history cannot satisfy it. No search, accounting-v14,
calibration, persisted schema, historical evidence or generated-record change.
The separate standalone MinBTL observed-Sharpe/arithmetic boundary is outside scope.

## Consequences, verification and reversal

Malformed available history cannot produce a verdict, while ordinary measured
history retains exactly the existing component conjunction and serialized result.
Tests must first reproduce infinity/boolean/array/type/range acceptance, then cover
nonpositive observed Sharpe, zero history/single-trial boundaries, exact negative
Fractions, finite representations and error precedence. Hypothesis verifies the
unchanged duration comparison and monotonicity for valid finite durations.
Independent research review and foreground make check-all precede delivery.

Remove only the duration guard to reverse; preserve the finding, which would reopen.
This validates one input's domain, not its acquisition provenance or the accuracy
of caller-supplied elapsed years.
