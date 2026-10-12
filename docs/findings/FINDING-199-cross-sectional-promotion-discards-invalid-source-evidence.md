# FINDING-199: Cross-sectional promotion discards invalid source evidence

- **Status:** Corrected
- **Date:** 2026-10-11
- **Severity:** High — invalid graduation claims become forward positions
- **Scope:** freeze_cross_sectional_graduate source projection
- **Decision:** ADR-250
- **Prior art:** ADR-145/FINDING-076, ADR-149/FINDING-079, ADR-249/FINDING-198

## Evidence

A synthetic xs_momentum experiment selects lookback 126. Changing only its
graduate to lookback 999 through unchecked model copies makes complete source
validation refuse the claim, but the existing freeze projection creates a valid
position with lookback 999. Independent reproduction also confirms graduate
strategy drift, failed graduate/best gates, unequal best-gate reasons, missing
selected strategy and searched-name disagreement are source-invalid yet promoted.
The position drops trial and gate evidence, so position validation cannot detect
these source contradictions.

This is an in-memory boundary defect, not an observed corrupt committed book,
broker order or measured false graduate. Validating experiment stores remain
protected. No real search, cohort, workflow, broker or generated data was changed.

## Correction and verification

ADR-250 specifies complete authoritative experiment reconstruction at projection
entry, before the original absence/snapshot/output branches. Independent pre-code
review approves this scope and preserves 32 exact complete baseline positions,
caller state and all 38 existing forward tests under a scratch wrapper.

Before implementation, nine source-copy regressions failed and 51 preservation
cases passed. After the one-line reconstruction, all 127 affected tests pass.
Independent final review approves 125 affected tests and 97 exact complete
published-baseline position JSON comparisons, including IC-subtype evidence,
present/absent lineage, full/partial/empty snapshots and structured/absent holdout.
Caller JSON is unchanged and all three legacy missing-snapshot refusal messages
match the baseline. Removing only the entry line restores the published whole-module
AST. The full foreground gate passes 5,048 backend and 363 frontend tests,
with 97.77% backend and 97.63% frontend statement coverage; lint and strict
typing pass.
No new source or paper criteria, thresholds, factor formulas, schema, broker
actions or generated records.
