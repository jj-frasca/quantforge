# FINDING-010: Calibration reconstructs the wrong finalist for a non-default selection rule

- **Severity:** High — methodology attribution and diagnostic identity
- **Found:** 2026-08-30 by Codex hostile review of ADR-069/070
- **Affected:** `backend/app/research/lab/calibration.py`
- **Decision:** ADR-071

## Finding

ADR-069 made the cross-family finalist rule a measured parameter. `run_search(select_by=
"walk_forward")` correctly sends the family with the highest walk-forward OOS Sharpe to the sealed
holdout and graduation gate. Calibration then discards that choice and reconstructs its finalist as
`max(experiment.trials, key=deflated_sharpe)`.

The two rules are explicitly expected to disagree; proving that was an ADR-069 acceptance test.
Consequently, a non-default null or power artifact can combine the selected family's gate verdict
with another family's:

- walk-forward and purged-CV diagnostics;
- finalist strategy name and category attribution;
- in-sample Sharpe and capture ratios; and
- reported selection-adjusted Sharpe for a false graduate.

The search fingerprint correctly identifies the artifact as `walk_forward`; the fields inside it
can nevertheless describe the default `observed` finalist.

## Impact on published decisions

ADR-070's default-stays-`observed` decision is not invalidated. Its pre-stated criterion used
graduation/detection counts, and those come from `Experiment.graduate` / `best_gate_result`, which
`run_search` computes from the genuinely selected family. The Type-I false-graduate counts are
likewise sound.

The ADR-070 observation that selecting on walk-forward did not raise the null distribution of that
statistic is not supported: the calibration recorded the max-DSR family's statistic. Any capture,
finalist-category, or strategy-name comparison from the non-default power run has the same identity
defect. The non-default artifacts were intentionally not committed, so no generated `data/*.json`
requires migration.

## Required correction

Calibration must use the same selection function and `select_by` value as `run_search` whenever it
extracts finalist-level fields. Tests must construct trials on which observed and walk-forward
selection disagree and prove both the null and power extraction paths follow the requested rule.
