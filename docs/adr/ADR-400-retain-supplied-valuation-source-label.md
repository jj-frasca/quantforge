# ADR-400: Retain the supplied valuation history source label

- **Status:** Accepted
- **Date:** 2026-10-28
- **Deciders:** Codex autonomous session14, ISO2026-W44
- **Addresses:** FINDING-336
- **Extends:** ADR-022/023/373/399

## Context and Alternatives

The actual scorer/provider silently replace a validated history's source label
with UndervaluationScore's SEC EDGAR default. Independent data/research reviews
confirm the mismatch and approve a narrow producer correction. Changing the model
default would reinterpret direct construction/legacy absence; reconstructing true
source provenance is unavailable at this boundary. Neither is adopted.

## Decision

Add only source=history.source to score_valuation's final UndervaluationScore
constructor. Retain every supplied validated string exactly, including empty
strings, without normalization, source constraints, extra validators or recovery.
The public model default, schema, historical labels, numeric calculations, flags,
thresholds, fingerprint and v14 stay unchanged. Earlier arithmetic/refusals still
precede construction. Malformed unchecked source values may newly fail existing
final string validation, including with other invalid output fields; accept that
availability cost without claiming unchanged final error ordering or fallback.

## Consequences and Verification

The output retains supplied attribution only. It does not authenticate a source,
establish per-fact/PIT/period truth, price provenance or producing code. Provider
scoring remains outside acquisition fallback and hunt errors stay per symbol.
Do not infer or rewrite historical labels; no source fetch, generated evidence,
calibration or cohort changes are authorized by this decision.

Before implementation capture290 complete ordinary claims/schema/whole AST.
Observe failing tests for direct/provider retention, source-only payload changes,
Unicode/empty strings, unchecked invalid metadata and provider/hunt propagation;
keep default SEC/legacy JSON and earlier arithmetic refusal controls. Use a string
roundtrip property. Require exact full baseline/schema/AST outside the single
keyword, independent final reviews, foreground make check-all, safe individual
publication and exact master CI verification.

Reversal removes the single keyword and reopens F336. Preserve this ADR/finding
and previously accepted records; never rewrite generated history.
