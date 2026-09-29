# FINDING-080: Experiment stores bypass claim validation

- **Severity:** High — unchecked model copies can persist invalid research-pool claims
- **Status:** Resolved by ADR-150
- **Date:** 2026-09-29
- **Affects:** ADR-016, ADR-024, ADR-145, and ADR-147 experiment stores

## Finding

ADR-145 and ADR-147 make cross-sectional and single-name experiment construction/reload complete
validated claim boundaries. Their JSON writers do not re-enter those boundaries: the monolithic
single-name store, partitioned single-name store, and cross-sectional store directly serialize
received model instances. Pydantic's `model_copy(update=...)` intentionally skips validation, so an
incoherent selected trial, graduate, gate verdict, or panel identity can be written successfully;
the pool then becomes unreadable when the next load correctly rejects it.

The in-memory stores are not durable and are outside this finding. Existing committed pool rows
already reload through the hardened models and require no rewrite.

## Required correction

Before any filesystem mutation, reconstruct every incoming experiment through its concrete model's
`model_validate(model_dump(round_trip=True))`. Apply this to the monolithic and partitioned
single-name writers and the cross-sectional JSON writer. Invalid input must raise while leaving an
existing file byte-for-byte unchanged. Do not alter retention, deduplication, trial accounting,
generated data, claim validation rules, or model schemas.
