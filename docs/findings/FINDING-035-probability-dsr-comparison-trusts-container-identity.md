# FINDING-035: Probability-DSR comparison trusts unbound container identity

- **Severity:** High
- **Status:** Resolved by ADR-103
- **Found:** 2026-09-22, Codex autonomous session 5
- **Affects:** ADR-102's probability-DSR comparison

## Finding

`compare_probability_dsr_gate` compares the top-level gate, search, and history fields on its two
null calibrations and `PowerSweep`, but does not bind those claims to the records it actually
counts. `PowerSweep` is a public Pydantic model and can be loaded directly with cells whose edge,
gate version, search version, or history differs from the sweep wrapper. Likewise, a joint verdict's
embedded `GateResult.gate_config_version` can differ from its calibration container.

The ordinary `collect_power_sweep` constructor rejects several of these inconsistencies, but the
analysis boundary accepts deserialized artifacts rather than requiring that constructor's call
history. Trusting only the wrapper would let mismatched verdicts contribute candidate/incumbent
discordance to the exact paired test while the report advertises a different procedure. Duplicate
strong-edge cells are also silently collapsed by a dictionary, making file order choose the cell.

## Required correction

Before computing any count, bind every power cell to the sweep's edge, gate/search version, and
history; bind every embedded `GateResult` to its calibration's gate version; and refuse duplicate
strong-edge cells. Keep the ADR-102 threshold, modes, sample floors, decision rule, and production
gate unchanged. Do not dispatch calibration or edit generated data.
