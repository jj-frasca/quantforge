# FINDING-195: Duplicate capture cells let file order select evidence

- **Status:** Corrected
- **Date:** 2026-10-11
- **Severity:** Medium — ambiguous paired research evidence
- **Scope:** ADR-057 compare_power_sweeps cell identity
- **Decision:** ADR-246
- **Prior art:** FINDING-035 / ADR-103, probability comparator

## Evidence

A before sweep accepts two phi=0.2 cells with capture 0.5 and 1.5. The after sweep
has one phi=0.2 cell with capture 1.0, a changed search version and finalist name.
compare_power_sweeps collapses the before cells by a last-write dictionary.
Reversing those before cells changes the attributable gross/net delta from -0.5
to +0.5. Two source records silently become one selected comparison row.
Independent synthetic reproduction confirms the sign reversal.

FINDING-035 already identified this duplicate-selection class and ADR-103 guarded
strong-edge cells in compare_probability_dsr_gate. The capture consumer remains
unguarded; this finding records that remaining path rather than reopening the
prior correction. No production duplicate, changed calibration rate or false
graduate is inferred; no real cohort, search or generated artifact was rerun.

## Correction and verification

ADR-246 requires unique existing effective keys on both sides before comparison
mappings, preserving all earlier identity refusals. A four-line local guard now
refuses repeated keys without selecting, pooling or deleting observations.

Before implementation, 20 duplicate-key regressions failed and three preservation
cases passed. The suite covers either side and input order, AR/band keys, signed
zero, legacy fallback collisions and identical records, with unique-order
Hypothesis cases, sorted unmatched output and search-refusal precedence.
Independent review approved 40 combined key/delta tests, 200 exact published-
baseline complete comparison-row JSON checks and six additional collision probes.
Removing only the guard restores the published full-module AST, including all
previous identity refusals and the original comparison key.

The full foreground backend/frontend delivery gate is required before shipping.
Producer/schema policy and nested wrapper identity remain separate; no attribution,
reference estimator, threshold or comparison key changes.
