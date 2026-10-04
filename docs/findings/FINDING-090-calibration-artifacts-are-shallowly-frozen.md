# FINDING-090: Calibration artifacts are shallowly frozen

- **Severity:** High — durable Type-I and power evidence can drift after validation
- **Status:** Resolved by ADR-158
- **Date:** 2026-10-03
- **Affects:** ADR-037, ADR-053, ADR-080, ADR-102, ADR-103

## Finding

`NullCalibration`, `PowerCalibration`, and `PowerSweep` declare `frozen=True`, but retain mutable
lists, dictionaries, and nested model graphs. Caller aliases and public mutation can change symbol
pairing, error counts, finalist probabilities, gate attribution, or sweep cells after the model's
relationship validators have passed. The workflow writers serialize these live objects directly,
so the committed evidence can differ from the validated claim. An unchecked `model_copy` can also
bypass artifact invariants before a consumer or consolidator uses it.

## Required correction

Defensively reconstruct and deep-freeze the complete calibration graph while preserving existing
JSON arrays/objects and legacy defaults. Revalidate calibration and sweep inputs at consolidation
and methodology-inference boundaries before reading or writing them. Do not change any statistic,
sample, seed, identity, gate, threshold, workflow dispatch, or generated artifact.
