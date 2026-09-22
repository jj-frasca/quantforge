# FINDING-028: Panel-null replicates may change the frozen symbol cohort

- **Severity:** High — the null distribution can apply a different statistic from the observed
  arm by taking each replicate's median over a data-dependent subset of symbols
- **Found:** 2026-09-21 by Codex hostile review of the unspent ADR-081 execution path
- **Status:** Resolved by ADR-092
- **Affected:** `PanelNullCohort`, cohort binding, whole-panel replicate execution and validation

## Finding

ADR-085 measures the observed statistic only after every frozen symbol completes one production
search on the exact common source panel. Any observed-symbol failure aborts preparation. The null
arm does not preserve that contract: `bind_panel_null_cohort` copies ADR-067's 30-symbol reporting
floor into `min_successful_symbols`, and `run_panel_null_replicate` takes its median over whichever
symbols happened to search successfully in that generated panel.

The current feasible cohort has 39 symbols. A null replicate may therefore discard as many as nine
symbols while remaining valid. Search failure can depend on the generated path, so the retained set
is data-dependent. Recording the errors and enforcing a minimum count makes the partial panel
auditable; it does not make its median the same equal-symbol functional applied to the observed
panel or to another null replicate.

## Impact

The 400 draws would not be exchangeable applications of one pre-registered panel statistic. Their
symbol composition could vary with generated data while the observed statistic always contains the
complete cohort. Tail counts and exact binomial intervals would then describe a mixture of
different estimands, not Monte Carlo uncertainty for the fixed ADR-081 statistic.

The panel-null measurement remains unspent, so no generated artifact requires migration.

## Required correction

Require every null replicate to search every frozen cohort symbol successfully. Bind the effective
symbol count to the complete cohort size, reject any lower value at the model boundary, and fail a
replicate after collecting its symbol-attributed errors rather than taking a partial median. Keep
the cohort, panels, seeds, diagnostics, tail procedure, and every validation threshold unchanged.

## Resolution

Resolved by ADR-092. The frozen cohort now requires `min_successful_symbols == len(symbols)`, the
production binding derives that exact value, and any symbol error invalidates the replicate before
it can contribute to a shard or the final calibration.
