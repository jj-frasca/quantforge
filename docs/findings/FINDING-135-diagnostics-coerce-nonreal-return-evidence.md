# FINDING-135: OOS diagnostics coerce nonreal return evidence

- **Date:** 2026-10-07
- **Severity:** Medium — malformed return payloads become measured selection evidence
- **Status:** Resolved — ADR-199

## Evidence

Both walk-forward and purged evaluators convert the complete performance matrix
and optional benchmark to float before checking source type. With first-column
returns `.01,.02,.03,.04`, negatives in the second column, train `[0,1]` and
test `[2,3]`, numeric strings publish OOS Sharpe approximately 78.57480512.
Adding imaginary component `1j` to every value publishes the same score after
NumPy discards it. Boolean and object arrays can likewise be reinterpreted as
returns. Shape validation does not establish measured real numeric evidence.

PBO already checks original dtype (ADR-189), protecting ordinary validated search
matrices; these public evaluators and their optional benchmark boundaries remain
independently callable. No corrupt production record or false graduate is claimed.

## Correction and limits

Require original matrix and benchmark dtype kind signed/unsigned integer or
real floating point before float64 conversion, retaining existing shape and
empty-split precedence. Reject boolean, complex, string, object and temporal
payloads. Keep complete valid numeric matrices, original estimator, selection,
calendar rows, all diagnostic defaults, thresholds and calibration identity.
