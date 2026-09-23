# FINDING-036: PBO ignores cross-family finalist selection

- **Severity:** High
- **Status:** Resolved by ADR-104
- **Found:** 2026-09-22, Codex autonomous session 6
- **Affects:** Longitudinal and cross-sectional graduation searches

## Finding

Both production searches evaluate concrete configurations inside several strategy families, choose
one finalist per family, and then select the overall winner across those finalists. The PBO sent to
the graduation gate is nevertheless computed only inside the winning family's grid. Candidates in
the other families, plus the adaptive refined grid in the longitudinal search, do not enter that
PBO calculation.

ADR-046 deliberately retained family-local PBO while repairing whole-search DSR and MinTRL, calling
it a diagnostic of the winning family's rank inversion. That statistic does not measure the
selection procedure the gate judges. A family can have a stable internal winner and low PBO while
the choice among many family winners is noise. The final cross-family argmax is the same omitted
selection layer ADR-046 already priced for DSR.

This is not repaired by whole-search DSR: PBO measures out-of-sample rank inversion across CSCV
splits, while DSR applies a multiple-testing haircut to observed Sharpe. Passing one does not make
the other cover an omitted selection step.

## Required correction

Compute the gate's PBO once over the complete matrix of every concrete configuration evaluated in
the current search, including the adaptive refined grid when present, and persist that same
procedure-level value on the family-finalist summaries. Keep parameter stability family-local,
because unrelated families do not form a parameter neighborhood. Do not change `pbo_max`, any
other validation threshold, candidate allocation, selection, or generated data locally. The
changed calibrated procedure requires fresh ordinary null and power measurements before their PBO
evidence is interpreted.
