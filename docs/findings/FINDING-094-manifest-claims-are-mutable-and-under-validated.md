# FINDING-094: Experiment manifests are mutable or accept invalid lineage identity

- **Severity:** High — durable research claims can retain impossible or changeable reproducibility identity
- **Status:** Resolved by ADR-163
- **Date:** 2026-10-04
- **Affects:** ADR-137, ADR-138, ADR-145, and ADR-147

## Finding

Standalone `ExperimentManifest` construction accepts an empty executed revision, strategy, parameter
hash, data source, symbol, adapter version, validation hash, and benchmark, plus a reversed request
range. It also accepts naive creation timestamps. Such a record still serializes as the lineage for a
scientific claim even though it cannot identify the code, inputs, configuration, or valid interval
that produced it.

`CrossSectionalManifest` validates more of its identity, but its component list remains mutable after
construction. A caller can clear or reorder the panel evidence after uniqueness and non-empty checks.
It also accepts empty shared strategy and benchmark identity, and an unchecked copied component can
bypass its own range or adapter validation before attachment. ADR-145/147 recursively freeze these
records inside complete experiments, but direct manifests remain unsafe before that attachment and
for any independent consumer.

A read-only compatibility audit found all 3,001 single-name manifests and all 4 panel manifests in
committed `data/*.json` compatible with the proposed timezone, hash, non-empty identity, interval,
and immutable-component invariants.

## Required correction

Make both manifest shapes authoritative standalone claims. Validate timezone-aware UTC creation,
full lowercase Git SHA and SHA-256 fields, non-empty shared identity, and proper request intervals;
normalize symbols consistently; defensively reconstruct and freeze ordered panel components; and
revalidate incoming model instances. Preserve existing JSON object/array shapes and every outer
experiment relationship. Do not change acquisition, quality checks, strategy selection, validation
methodology, thresholds, workflows, or generated records.
