# ADR-213: Validate null-calibration leaf evidence

- **Status:** Accepted
- **Date:** 2026-10-08
- **Deciders:** Codex autonomous session 17, ISO 2026-W41
- **Resolves:** FINDING-158
- **Extends:** ADR-158, ADR-080, ADR-037

## Context

`NullGraduate` and `NullSymbolDiagnostics` are frozen but accept nonfinite
scores, nonpositive or coerced history, and invalid probabilities. ADR-158
reconstruction cannot enforce contracts absent from the authoritative leaves.
A NaN graduate can survive consolidation, silently fail ADR-018's comparison,
and serialize its invalid score as null.

## Decision

Validate original evidence at both leaves: score values must be finite,
float-representable real nonboolean numbers; history counts must be positive
nonboolean integers; holdout years must be finite and strictly positive; and
present probability DSR must be finite and in [0, 1]. Preserve legitimate
signed and zero scores, numpy numeric scalars, absent nullable diagnostics,
absent joint verdicts, and the existing JSON shapes. Reject invalid evidence
without clamping, dropping rows, or inventing unmeasured defaults.

Existing nested reconstruction and merge boundaries inherit these contracts.
No estimator, selection, sample, threshold, calibration fingerprint, workflow,
or generated data changes. Current frozen offline runs retain their executed
revision and only complete audited results may be interpreted.

## Alternatives considered

1. Validate only at merge: standalone leaves and JSON reload would remain unsafe.
2. Replace invalid scores with None or omit records: changes the denominator and
   turns malformed evidence into an invented missing measurement.
3. Harden every calibration scalar in one change: broader than these reproduced
   defects; legacy top-level arrays and derived arithmetic need separate findings.

## Verification and limits

Observe RED direct-construction/JSON and unchecked-copy attachment/merge tests.
Protect negative/zero finite scores, supported numeric scalar types, probabilities
at 0/1 and explicit or absent None. Read committed null artifacts without writing
them, then run focused consumers and full foreground gates.

This establishes leaf validity, not whole-artifact scalar coherence, symbol
identity, or overflow-free subtraction of otherwise finite diagnostics.

## Reversal

Remove the leaf field validators and bounds. This reopens FINDING-158 without
changing valid calibration arithmetic.
