# FINDING-015: Pool reporting reconstructs the wrong non-default finalist

- **Severity:** High — methodology attribution and real-versus-null identity
- **Found:** 2026-08-30 by Codex follow-up review of FINDING-010 / ADR-071
- **Status:** Resolved by ADR-078
- **Affected:** `backend/app/research/lab/pool_report.py`

## Finding

ADR-071 corrected null and power calibration so a non-default `select_by="walk_forward"` run
extracts diagnostics from the family that production actually selected. The real-pool side still
reconstructs its finalist with `max(trials, key=deflated_sharpe)` in every reporting path.

`run_search` persists only the production choice's `Experiment.best_strategy_name`. When the
walk-forward and observed rules disagree, pool diagnostics, excess-return comparisons, category
attribution, probability agreement, capture, and window comparisons can therefore describe the
max-DSR family while the experiment verdict and matching calibration describe the walk-forward
family. The search fingerprint says the procedures match even though the values do not.

## Impact

The default `observed` rule is unaffected because its selected family is max DSR. Non-default
experiments are misattributed in reports. ADR-070's default decision remains supported by its gate
counts, but the reporting layer is not safe for a future non-default production choice.

## Required correction

Strategy name is insufficient because refinement can append a second trial from the same family.
New experiments must persist the exact selected trial index, and pool reporting must use one helper
to resolve it wherever it means “the experiment's finalist.” Legacy experiments with no persisted
index may use the historical max-DSR reconstruction. An invalid or name-inconsistent persisted
index must be refused, not silently replaced by a different family.
