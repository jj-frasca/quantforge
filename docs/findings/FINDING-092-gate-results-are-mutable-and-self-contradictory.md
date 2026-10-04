# FINDING-092: Gate results are mutable and can contradict their own verdict

- **Severity:** High — a graduation claim can change or disagree with its component evidence
- **Status:** Resolved by ADR-160
- **Date:** 2026-10-04
- **Affects:** ADR-015, ADR-016, ADR-102, ADR-147, and ADR-159

## Finding

`GateResult` declares `frozen=True`, but its public `reasons` list remains mutable. A caller can
therefore change the serialized explanation after construction while retaining the same result
object and verdict. Direct construction also accepts a `passed` value that contradicts the six
component booleans, a NaN or negative required track-record length, an empty gate-configuration
identity, and only one member of the structured holdout pair. NaN serializes as JSON `null`.

Outer experiment and calibration artifacts defensively freeze their nested gate result, but that
does not make the shared model coherent at direct construction, before attachment, or in another
consumer. A hostile or unchecked result can therefore misstate the deterministic graduation
conjunction that ADR-016 says the agent cannot override.

A read-only compatibility audit found all 4,055 gate-result occurrences in committed JSON already
satisfy the proposed conjunction, structured-holdout pairing, non-negative required-length, and
non-empty-version invariants.

## Required correction

Make `GateResult` itself defensively immutable and self-validating. Derive its permitted `passed`
value from the six component booleans, require a non-negative/non-NaN required track-record length,
a non-empty gate configuration version, and either both structured holdout fields or neither.
Preserve positive infinity for MinTRL because it is the defined result for a non-positive observed
Sharpe. Revalidate a gate result before calibration counterfactual inference. Do not change any
gate component, threshold, reason text, or graduation formula.
