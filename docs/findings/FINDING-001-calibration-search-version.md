# FINDING-001: Calibration artifacts do not identify the search they measured

- **Severity:** High (methodology lineage; stale Type-I/power claims can look current)
- **Status:** Fix proposed in ADR-044
- **Affected:** ADR-036, ADR-037, ADR-041, ADR-042; `NullCalibration`, `PowerCalibration`

## Finding

QuantForge describes null calibration as the empirical Type-I error of the **whole pipeline**, but
versions the result only with `GateConfig.version_hash`. The whole pipeline also includes the
strategy family, each catalog-derived parameter grid, and `n_per_param`. Those inputs determine
how many hypotheses are searched and which finalist reaches the gate.

Two calibrations can therefore share a `gate_config_version` while measuring different statistical
procedures. `merge_calibrations` currently accepts those shards, and the committed/dashboard result
has no field by which a reader can distinguish an old catalog calibration from the current one.

## Evidence

- `GateConfig.version_hash` hashes only threshold fields in `backend/app/research/lab/gate.py`.
- `calibrate_gate` passes `strategy_names` and `n_per_param` into `run_search` but stores neither a
  fingerprint nor the resolved grids.
- `merge_calibrations` rejects different gate hashes and null modes only.
- The scheduled workflow says the answer is a property of `GateConfig`, although its own headline
  correctly calls it the Type-I error of search + gate together.

## Impact

The published 1.0% measurement is not shown to be wrong for its original run. The unsafe claim is
that the same artifact continues to characterize a modified catalog/search merely because the six
gate thresholds did not change. Trial-family changes are precisely what multiple-testing controls
must track.

## Required behavior

Artifacts must fingerprint the resolved hypothesis family, and sharded consolidation must reject
different fingerprints. Legacy artifacts must remain readable but be marked as unspecified until
the workflow's sole writer refreshes them.
