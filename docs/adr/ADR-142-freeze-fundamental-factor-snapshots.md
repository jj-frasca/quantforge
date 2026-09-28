# ADR-142: Freeze fundamental score snapshots with cross-sectional experiments

- **Status:** Accepted
- **Date:** 2026-09-27
- **Deciders:** Codex autonomous session 29 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-073
- **Extends:** ADR-025, ADR-029, ADR-138, and ADR-140

## Context

Value and quality factors are functions of a price panel plus static fundamental score mappings.
ADR-025 requires the selected factor configuration to remain locked during forward testing, while
ADR-029 explicitly treats the current fundamentals pool as an as-of snapshot. Persisting prices and
parameters without the score mappings does not preserve that claim. Reloading a later pool would
introduce revised filings, newly swept names, and changed ranks across the frozen universe.

## Options Considered

1. **Persist the exact panel-projected score snapshots on the experiment and position.**
   - Pro: makes every searched trial and forward factor self-contained and preserves missingness.
   - Con: adds two nullable mappings to durable experiment and position rows.
2. **Reload the fundamentals pool during each forward run.**
   - Pro: uses the newest available fundamental view.
   - Con: changes historical ranks and is re-fitting, not forward-testing the frozen graduate.
3. **Disable fundamental factors in forward testing.**
   - Pro: avoids reconstructing an unknown factor.
   - Con: abandons ADR-029 graduates after they pass the same statistical gate as price factors.

## Decision

`run_cross_sectional_search` freezes the supplied value and quality mappings after projecting them
onto the price-panel columns in panel order. `CrossSectionalExperiment` persists both nullable
snapshots: `None` means the factor family was not supplied; a mapping preserves the exact scored
symbols and values, including deliberate missingness within the panel.

Promotion copies those snapshots from the experiment into `CrossSectionalPosition`. It accepts no
replacement map from the caller. Forward registry reconstruction supplies both frozen snapshots, so
`xs_value`, `xs_quality`, and `xs_quality_value` reproduce the discovery signal. A legacy
fundamental graduate lacking its required snapshot is left unpromoted for that cycle; it is never
silently rebuilt from current data. Price-only legacy graduates remain promotable.

No factor formula, price universe, gate, benchmark, lifecycle threshold, or point-in-time caveat
changes.

## Consequences

- New cross-sectional experiments contain every non-price input needed to reproduce their trials.
- Fundamental graduates can accrue a real forward record without a mutable external pool.
- The persisted mappings grow rows modestly but are bounded by the retained panel universe.
- Legacy fundamental graduates without snapshots remain visible but cannot make a new forward claim.

## Reversal

Remove the snapshots and reload live fundamentals during forward runs. That would make a frozen
factor depend on future pool state and is not recommended.
