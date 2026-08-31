# ADR-071: Preserve the selected finalist throughout calibration

- **Status:** Accepted
- **Date:** 2026-08-30
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Acts on:** ADR-069 (selection rule as a measured parameter)
- **Relates to:** ADR-044 (calibration identity), ADR-049/057/059 (attribution)
- **Finding:** `docs/findings/FINDING-010-calibration-reconstructs-the-wrong-finalist.md`

## Context

`run_search` selects a family under the requested `select_by` rule and uses that family for the
holdout and gate. Calibration later calls `_finalist`, which always returns max DSR. That was
equivalent while observed Sharpe was the only rule because every family shares the same whole-search
haircut. It is not equivalent under ADR-069's walk-forward rule, and ADR-069 specifically measures
the cases where the rules disagree.

The artifact therefore has two competing finalist identities: gate outcomes from the requested
rule, and diagnostics/attribution reconstructed under the default rule.

## Decision

Calibration will resolve finalist-level fields with the same `_select_index(trials, select_by)`
function used by `run_search`.

1. `_finalist` takes the requested `SelectBy` and delegates to the shared selection function.
2. Null diagnostics, false-graduate DSR, power finalist Sharpe, strategy name, category attribution,
   and capture inputs all use that selected trial.
3. The default remains `observed`; no production selection behavior, gate threshold, fingerprint,
   or generated artifact changes.
4. ADR-070's detection and Type-I counts remain accepted. Its one observation about the
   non-default null statistic is marked unsupported by FINDING-010 and must not be reused without a
   corrected rerun.

## Alternatives considered

1. **Use `Experiment.best_strategy_name`.** Rejected: refinement can leave coarse and refined trials
   with the same strategy name, so a name does not identify the selected trial.
2. **Store a selected trial index on every experiment.** Exact, but unnecessary schema growth: the
   rule and immutable trial list are already present at calibration time and selection is
   deterministic.
3. **Leave attribution on max DSR because only detection gates.** Rejected: ADR-049/057/059 made
   attribution part of the methodology precisely so a composite result can be interpreted. An
   artifact whose verdict and diagnostics describe different finalists is not self-consistent.

## Consequences

- Future non-default sweeps remain internally consistent across verdict, diagnostics, and
  attribution.
- Existing committed default-rule artifacts are byte-for-byte semantically unchanged.
- No cloud rerun is required to protect production because the non-default arm did not become the
  default and its artifacts were not committed. A future comparison must rerun the corrected arm.

## Reversal

Restore unconditional max-DSR reconstruction. That intentionally restores FINDING-010 whenever a
non-default selection rule is measured.
