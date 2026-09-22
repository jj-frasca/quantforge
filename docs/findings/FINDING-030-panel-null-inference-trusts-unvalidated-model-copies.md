# FINDING-030: Panel-null inference trusts unvalidated model copies

- **Severity:** Medium — an in-process caller can bypass the complete-artifact contract and obtain
  tail inference from a partial or identity-drifted calibration
- **Found:** 2026-09-22 by Codex hostile review of the unspent ADR-081 inference boundary
- **Status:** Resolved by ADR-098
- **Affected:** `infer_panel_null`, any future in-process consumer of a copied calibration model

## Finding

`PanelNullCalibration` validates the complete frozen index set, ordering, seeds, derived panel IDs,
symbol completeness, and cohort identity during normal construction and JSON loading. However,
Pydantic's `model_copy(update=...)` deliberately does not validate updates. `infer_panel_null`
accepts an existing model instance and immediately computes tail counts, so a caller can remove a
replicate or replace the cohort after construction and still obtain an apparently valid inference.

The current consolidation and recovery commands deserialize or construct validated artifacts, so
this does not change an existing measurement. It leaves the scientific inference function itself
weaker than the artifact contract it claims to interpret and makes a future in-process caller a
possible validation bypass.

## Required correction

Revalidate the complete calibration from its serialized field values at the inference boundary
before reading either the real or null statistic. Preserve every seed, replicate, statistic,
confidence rule, gate, and validation threshold.

## Resolution

Resolved by ADR-098. `infer_panel_null` now reconstructs the complete validated calibration before
computing either diagnostic, so partial, reordered, identity-drifted, or otherwise invalid model
copies fail before tail inference.
