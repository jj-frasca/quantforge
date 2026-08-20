# ADR-044: Version the calibrated search space, not only the gate thresholds

- **Status**: Accepted
- **Date**: 2026-08-20
- **Deciders**: Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Extends**: ADR-036 (null calibration), ADR-037 (sharded publication), ADR-041/042 (power)

## Context

The null and power calibrations run the whole research procedure: resolve strategy names through
the catalog, generate each parameter grid, select family winners, select the overall finalist, and
apply `GateConfig`. Their measured Type-I error and power therefore depend on both the gate
thresholds and the searched hypotheses.

The artifacts record only `gate_config_version`, a hash of six threshold fields. Adding a strategy,
changing a catalog bound, changing `n_per_param`, or changing which subset of the catalog is passed
to calibration leaves that hash unchanged even though it changes the number and shape of trials.
ADR-037 then permits shards from those different searches to merge because it checks only the gate
hash and null mode. The dashboard can consequently present an old false-graduation rate as if it
described the current search.

This is a versioning defect, not evidence that the measured 1% result was numerically wrong for the
34-strategy search that produced it. It means the artifact does not carry enough identity to know
what procedure the number belongs to.

## Decision

Add a deterministic `search_config_version` to null and power calibration artifacts. Hash:

- the `GateConfig` version;
- `n_per_param`;
- the requested strategy names in selection order; and
- every concrete parameter dictionary produced by the current catalog grid for each name.

The resolved grids, rather than catalog prose or bounds alone, are the hypotheses the search
actually tests. Preserving strategy order matters because ties resolve by first occurrence.

`merge_calibrations` must refuse shards with different `search_config_version` values even when
their gate hashes and null modes match. Existing committed artifacts deserialize with the explicit
sentinel `legacy-unspecified`; they remain readable but honestly advertise that their search space
was not fingerprinted. The next scheduled calibration replaces them through the existing sole
writer.

No threshold, gate verdict, strategy, or generated data file changes in this ADR.

## Alternatives considered

1. **Treat `gate_config_version` as sufficient.** Rejected: the measured object is explicitly the
   whole pipeline, and selection multiplicity changes outside `GateConfig`.
2. **Hash the strategy names only.** Rejected: changing a parameter bound or `n_per_param` changes
   the trial family without changing a name.
3. **Hash the entire Git commit.** Complete but too coarse: unrelated frontend or documentation
   edits would invalidate a scientific measurement. A future artifact may additionally record the
   source revision for provenance, but compatibility should turn on the resolved search spec.
4. **Invalidate the published 1% result immediately.** Rejected: the result remains evidence for
   the exact catalog at the run that produced it. The defect is missing lineage for future reuse.

## Consequences

- Calibration shards from different hypothesis families fail loudly instead of silently pooling.
- A catalog/grid change creates a visibly different calibration identity even when thresholds stay
  fixed, making the need to re-run detectable.
- Legacy artifacts remain API-compatible and are labelled rather than rewritten locally, preserving
  ADR-030's single-writer rule.

## Reversal

Remove `search_config_version`, its fingerprint helper, and the merge guard. Gate behavior and
stored experiments are otherwise untouched.
