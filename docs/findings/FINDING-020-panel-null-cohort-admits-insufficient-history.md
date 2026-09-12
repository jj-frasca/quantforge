# FINDING-020: Panel-null cohort admits symbols that cannot supply the frozen history

- **Severity:** High — the pre-registered measurement fails during preparation before any panel
  replicate can run
- **Found:** 2026-09-12 by Codex hostile review of ADR-081 cohort preparation
- **Status:** Resolved by ADR-084
- **Affected:** `select_panel_null_cohort`, `prepare_panel_null_source`,
  `panel-null-calibration.yml`

## Finding

ADR-081 requires one complete source panel with exactly `target_n_bars` rows for every frozen
symbol. The real-cohort selector instead reuses ADR-064's symmetric comparison band and accepts an
experiment when its history is within ±10% of the target. A symbol with fewer than 7,400 available
bars can therefore enter the immutable cohort even though source preparation later intersects all
selected calendars and refuses fewer than 7,400 complete rows.

The tolerance is appropriate for a descriptive real-versus-null report. It is not a feasibility
rule for a generator that must physically construct an exact-length panel.

## Evidence

On committed master data at `2362be57`, using the current search/gate fingerprints and the
production 7,400-bar target:

- 445 matching retained experiments collapse to 89 equally weighted symbols;
- 50 of those 89 symbols have fewer than 7,400 bars, with a minimum of 6,691;
- only 39 meet the exact source-history floor, still above ADR-081's fixed 30-symbol minimum; and
- `prepare_panel_null_source` takes the common calendar across all 89 and must fail when that
  calendar cannot contain 7,400 rows.

The measurement has not been dispatched, so no generated artifact or published panel inference is
affected.

## Impact

An authorized dispatch would spend preparation runner time and then fail before the first of 400
panel replicates. More importantly, allowing a shorter real history into an exact-length null panel
would make the frozen cohort identity claim a source history that the symbol cannot supply. This is
an execution and methodology-identity defect, not evidence for changing any validation threshold.

## Required correction

Keep ADR-064's upper history tolerance for the real estimand, but require every experiment admitted
to the panel-null cohort to have `n_bars >= target_n_bars`. Apply the floor before per-symbol repeat
medians and before the 30-symbol check. Source preparation remains the final authority and still
fails closed if the fetched common calendar is shorter than the target.
