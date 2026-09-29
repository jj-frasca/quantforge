# FINDING-077: Single-name experiment claim graph is shallow-frozen

- **Severity:** High — one durable experiment can serialize a different research claim under the same identity
- **Status:** Resolved by ADR-147
- **Date:** 2026-09-28
- **Affects:** ADR-014, ADR-016, ADR-017, ADR-023, ADR-029, ADR-079, and ADR-137 experiment records

## Finding

`Experiment` and its nested Pydantic models declare `frozen=True`, but the persisted single-name
claim graph still exposes mutable lists and dictionaries. A caller can reorder searched strategies
or trials, alter a trial or graduate parameter, append gate, fundamentals, distress, valuation, or
quality reasons, and change a quality issue context after construction. The next JSON serialization
then records different selection, verdict, business evidence, or acquisition evidence under the
original experiment UUID, timestamp, selected-trial index, and manifest hashes.

Construction also validates only part of the graph. Hostile JSON can persist a selected index,
graduate, best gate result, or manifest that describes a different trial while passing the current
lineage validator. The production universe path additionally attaches valuation evidence with an
unvalidated `model_copy(update=...)`, bypassing construction validation for that final claim.

## Required correction

Deep-freeze the complete `Experiment` claim graph at construction and JSON load, using defensive
copies so caller-owned inputs and shared nested models cannot mutate the record. Preserve the
existing JSON object/array schema and the documented legacy selected-trial fallback. Revalidate the
ordered strategy/trial identity, selected trial, graduate, best gate result, manifest, fundamental,
valuation, distress-veto, and quality-evidence relationships. Production enrichment must return
through the validated boundary rather than inject evidence with an unchecked model copy. Do not
change strategy formulas, selection rules, gate thresholds, or generated data.

## Resolution

`Experiment` now defensively reconstructs every nested Pydantic record and recursively freezes its
JSON-compatible lists and dictionaries. Construction and reload bind ordered trials, ADR-079
selection, graduate, best gate result, manifest hashes, symbol-bearing business evidence, vetoes,
and quality lineage as one claim. Universe valuation enrichment now re-enters model validation.
Regression coverage proves caller-owned and public nested mutation cannot alter the claim and that
hostile selection, graduate, manifest, symbol, and veto drift is rejected.
