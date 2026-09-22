# ADR-098: Revalidate the complete panel-null artifact before inference

- **Status:** Accepted
- **Date:** 2026-09-22
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Acts on:** FINDING-030
- **Extends:** ADR-081, ADR-092, ADR-097

## Context

ADR-081 requires exactly 400 complete whole-panel replicates. ADR-092 requires every replicate to
apply the complete frozen symbol estimand, and ADR-097 re-derives every persisted panel identity.
Those invariants run when `PanelNullCalibration` is constructed or deserialized.

Pydantic model instances can nevertheless be copied with unvalidated updates. The inference
function currently trusts its typed argument and can therefore calculate fixed-tail results from a
partial or identity-drifted copy that could not pass the artifact boundary.

## Decision

At the start of `infer_panel_null`, dump the supplied model's field values and reconstruct a
`PanelNullCalibration` through normal validation. Compute both primary and optional secondary
diagnostics only from that validated reconstruction.

This is a boundary hardening change. It does not change any valid artifact's statistic, seed,
replicate, panel identity, confidence interval, resolution, gate, or validation threshold.

## Consequences

- Inference cannot become a validation bypass for future in-process callers.
- Partial, reordered, cohort-drifted, seed-drifted, or panel-ID-drifted copies fail before a tail
  count is computed.
- Valid consolidation and recovery behavior is unchanged apart from one defensive reconstruction.

## Reversal

Removing the reconstruction restores FINDING-030 and would require every inference caller to prove
that no unvalidated model copy can reach the function.
