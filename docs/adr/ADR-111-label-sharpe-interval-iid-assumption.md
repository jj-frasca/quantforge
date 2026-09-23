# ADR-111: Label the Sharpe interval's iid-normal assumption

- **Status:** Accepted
- **Date:** 2026-09-23
- **Deciders:** Codex autonomous session 8 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-040
- **Supersedes in part:** ADR-109's unqualified confidence-interval presentation

## Context

ADR-109 added a useful sampling-uncertainty band using the iid-normal asymptotic Sharpe standard
error. The implementation and tests are internally consistent, but the returned object and UI call
it simply a 95% confidence interval. Lo (2002) explicitly distinguishes iid, stationary, and
time-aggregated return processes; strategy returns need not satisfy the special case implemented
here. FINDING-040 shows that the artifact drops the estimator assumption and that the public helper
does not validate its confidence domain.

A serial-correlation-robust replacement would require a separate estimator decision: HAC lag
selection or bootstrap block length materially affects coverage. No evidence in this review chooses
among those alternatives. Honest metadata is preferable to silently presenting the current special
case as general or improvising a new method without calibration.

## Decision

Keep ADR-109's numeric estimator unchanged and make its scope explicit. Every non-null
`SharpeConfidenceInterval` carries the literal assumption `iid_normal`; the API view and frontend
Zod/type boundary require that value. The dashboard renders “IID-normal 95% interval” and explains
that serial correlation or non-normal returns can make the range too narrow. Documentation uses the
same qualified name wherever it describes the field.

`sharpe_confidence_interval` rejects a non-finite confidence level or any value outside the open
interval `(0, 1)` before reading the return series. The one-year minimum and numeric bounds remain
unchanged. This decision adds provenance and input validation only; it does not claim robust
coverage or authorize a gate/statistic change.

## Alternatives considered

1. **Leave the assumption only in Python documentation.**
   - Pro: no wire-format change.
   - Con: API consumers and dashboard readers still receive an unqualified interval.
2. **Replace the interval immediately with HAC or block-bootstrap inference.**
   - Pro: can account for temporal dependence under additional choices.
   - Con: lag/block selection is a new methodology decision without coverage evidence and can make
     the same observed series produce materially different bands.
3. **Expose the iid-normal assumption durably and validate confidence now.**
   - Pro: makes the current calculation honest without changing its values and leaves a robust
     estimator as a separately reviewable future unit.
   - Con: adds one required nested response field and a more qualified UI label.

## Consequences

- No reader can mistake the current interval for dependence-robust inference from the artifact
  alone.
- Existing valid 95% bounds are numerically unchanged; API/frontend consumers gain a required
  literal nested field.
- Invalid confidence levels fail with `ValueError` instead of emitting infinite, `NaN`, collapsed,
  or reversed bounds.
- Any future robust interval needs its own ADR, method identity, and coverage tests rather than
  replacing `iid_normal` values in place.

## Reversal

Remove the assumption field/label and confidence validation. That would restore ambiguous or
malformed statistical evidence and is not recommended.
