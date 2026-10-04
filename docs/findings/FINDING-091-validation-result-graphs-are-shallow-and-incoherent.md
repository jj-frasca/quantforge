# FINDING-091: Validation result graphs are shallow and internally unbound

- **Severity:** High — a validated methodology report can drift or serialize invalid evidence
- **Status:** Resolved by ADR-159
- **Date:** 2026-10-04
- **Affects:** ADR-038, ADR-039, ADR-078, ADR-158

## Finding

`ValidationReport`, `WalkForwardResult`, and `PurgedCVResult` declare `frozen=True`, but retain
mutable lists and dictionaries. Public mutation can remove split/fold evidence, change flags and
interpretations, or replace regime evidence after construction while the report keeps the same
headline values and pass verdict. Caller-owned containers are not a durable boundary.

Direct construction also accepts non-finite Sharpes, out-of-range consistency, negative counts,
and result counts that disagree with their nested split/fold records. Pydantic serializes accepted
`NaN` and infinity as JSON `null`; a report can therefore be `passed=True` in memory while its
serialized methodology fields are no longer numbers. Unchecked `model_copy` values can reach the
gate or API without another authoritative validation step.

## Required correction

Defensively reconstruct and freeze the complete validation result graph. Reject non-finite values
and incoherent count/summary relationships at model construction, and revalidate reports at gate
and API consumer boundaries before use. Preserve the existing JSON object/array schema, diagnostic
definitions, split algorithms, pass formula, and every threshold.
