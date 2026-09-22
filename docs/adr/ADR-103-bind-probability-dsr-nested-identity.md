# ADR-103: Bind nested identity at the probability-DSR analysis boundary

- **Status:** Accepted
- **Date:** 2026-09-22
- **Deciders:** Codex autonomous session 5 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-035
- **Extends:** ADR-102

## Context

ADR-102 requires matched gate, search, and history identity before its paired comparison is
interpretable. Its executable boundary initially checked only the two null containers and the
`PowerSweep` wrapper. Those wrappers are not cryptographic envelopes: Pydantic can deserialize a
sweep containing incoherent cells, and each joint verdict contains the gate version that actually
produced its incumbent result. FINDING-035 shows that counting nested records without binding these
identities could combine different procedures under one advertised comparison.

## Decision

`compare_probability_dsr_gate` must fail before inference unless:

1. every power cell matches its sweep's edge, gate version, search version, and exact history;
2. every null and power joint verdict's embedded `GateResult.gate_config_version` matches its
   calibration container; and
3. each pre-registered strong AR(1) direction appears exactly once.

These checks apply at the consumer boundary even where an ordinary producer already enforces the
same invariant. Persisted artifacts are untrusted inputs, and the consumer cannot rely on the
constructor path used before serialization.

This decision changes no probability threshold, sample floor, power/null cell, acceptance
criterion, production gate, workflow, or generated artifact. It only refuses internally
incoherent evidence.

## Alternatives considered

- **Rely on `collect_power_sweep`.** Rejected: direct model deserialization bypasses that function.
- **Validate only power-cell wrappers.** Rejected: the embedded incumbent verdict can still come
  from another gate version.
- **Select the first or last duplicate cell.** Rejected: file ordering must not select evidence.

## Consequences

- ADR-102's report now proves that the nested observations it counts belong to the procedure and
  history named by their containers.
- Legacy or hand-edited incoherent artifacts fail closed rather than producing a comparison.
- Valid ordinary artifacts and all statistical criteria are unchanged.

## Reversal

Remove the nested identity checks. This would restore acceptance of artifacts whose counted records
cannot be attributed to the advertised matched procedure and is not recommended.
