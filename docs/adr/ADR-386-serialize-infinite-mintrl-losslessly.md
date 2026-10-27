# ADR-386: Serialize intentional infinite MinTRL losslessly

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Codex autonomous session7, ISO2026-W44
- **Resolves:** FINDING-328 within validated GateResult JSON serialization
- **Extends:** ADR-015/102/147/158/160

## Context

Positive infinite required track-record length is an intentional scientific
result for nonpositive observed Sharpe. Pydantic's default JSON conversion writes
null, which cannot reload into the nonnullable float. Actual nested experiment/
calibration controls and a flat-source official calibration mechanics control
reproduce the loss. Existing Python-JSON store writers retain bare nonstandard
Infinity instead. Independent reviews approve a lossless field-specific policy;
a 617-file scan found only finite current leaves, so no historical incidence or
migration is established.

## Options Considered

1. **JSON-only field serializer with positive-infinity string tag (chosen).**
   - Pro: covers both model_dump_json and model_dump(mode="json") writers, nested
     graphs and API responses; existing float readers already accept the tag.
   - Con: changes the serialization schema to number-or-literal-"Infinity";
     external readers need awareness, and historical nulls stay unrecoverable.
2. **ConfigDict ser_json_inf_nan="strings".**
   - Pro: concise and fixes ordinary Pydantic JSON text for this model.
   - Con: leaves Python mode="json" dumps containing float infinity, missing
     current stores/strict-JSON encoding; broader config can affect other fields.
3. **Use null or a large finite sentinel, or reject infinite MinTRL.**
   - Pro: superficially simpler finite-number-only output.
   - Con: conflates a defined impossible requirement with missingness, invents a
     finite duration, or changes ADR-015's scientific domain. Rejected.

## Decision

Add a field_serializer for GateResult.required_track_record_years with
when_used="json", annotated float | Literal["Infinity"]. Return "Infinity" only
when the validated value equals positive infinity; otherwise return its value.
Native Python-mode dumps keep numeric infinity. Preserve every field, finite JSON
value/byte representation, nullable legacy holdout semantics, constructor coercion
and validation, gate math/verdict/threshold, search identity and accounting-v14.
No decoder, fallback, null-to-infinity repair, root writer or generated-data edit.

## Consequences

Valid direct/nested JSON becomes strict JSON and round-trippable for this defined
infinite leaf. Existing authoritative float readers accept the literal already;
old bare-Infinity PythonJSON remains readable where current readers permit it.
New serialization/OpenAPI schema exposes number-or-literal-"Infinity" and external
clients must understand the tag. Current frontend schemas strip these unmodeled
nested verdict fields; no displayed numeric control or UI flow changes.

This policy does not certify unchecked invalid copies, unrelated nonfinite values,
source provenance or historical lost evidence. It changes representation, not a
statistic or graduation decision; no calibration refresh is inferred necessary.
The earlier scratch null-protocol draft tentatively used this unadopted number;
no such ADR/cohort/source was adopted. Null execution is deferred while this real
serialization defect takes priority; its mathematical design remains unspent.

Use actual RED for direct/nested dump routes, both store writers, official flat
calibration and read-only API/schema. Capture finite complete-artifact JSON and
native-Python replay before source; preserve constructor invalidity controls and
Hypothesis finite round trips. Obtain final independent reviews, foreground full
gates, safe individual push and exact CI verification.

## Reversal

Remove the serializer and imports. That restores null loss/nonstandard Infinity;
it does not repair historical data or change intentional MinTRL infinity.
