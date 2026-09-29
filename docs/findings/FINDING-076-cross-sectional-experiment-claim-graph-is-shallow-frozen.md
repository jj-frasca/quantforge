# FINDING-076: Cross-sectional experiment claim graph is shallow-frozen

- **Severity:** High — one durable experiment can serialize a different research claim under the same identity
- **Status:** Resolved by ADR-145
- **Date:** 2026-09-28
- **Affects:** ADR-024, ADR-138, and ADR-142 cross-sectional experiment records

## Finding

`CrossSectionalExperiment` and its nested Pydantic models declare `frozen=True`, but the persisted
claim graph still exposes mutable lists and dictionaries. A caller can append or reorder universe
symbols, replace strategy names, change a trial or graduate parameter, append gate reasons, duplicate
manifest components, or mutate an embedded quality issue's context after construction. The next
JSON serialization silently records those altered values under the original experiment UUID,
timestamp, manifest hashes, and gate identity.

This is not only a presentation defect. Universe order defines the searched panel and fundamental
snapshot projection; trial and graduate parameters define the selected factor; gate reasons describe
the durable verdict; manifest components and quality reports define the evidence behind the claim.
Mutation can also invalidate relationships that were checked only once during construction.

## Required correction

Deep-freeze the complete `CrossSectionalExperiment` claim graph at its model boundary, using
defensive copies so caller-owned inputs and shared nested model instances cannot mutate the record.
Preserve the existing JSON object/array schema and legacy nullable lineage behavior. Revalidate the
full graph on JSON load, including selected-trial, graduate, gate-result, and panel-lineage
relationships. Do not change factor formulas, search selection, gate thresholds, or generated data.

## Resolution

`CrossSectionalExperiment` now defensively reconstructs every nested Pydantic record, recursively
freezes JSON-compatible lists and dictionaries, and preserves the existing JSON array/object
representation. The boundary also requires ordered strategy names to match trials and binds any
graduate to the selected trial and exact best gate verdict, including structured holdout identity.
Regression coverage proves caller-owned and public nested mutation cannot alter the claim and that
hostile strategy, graduate, and gate-result drift fails during deserialization.
