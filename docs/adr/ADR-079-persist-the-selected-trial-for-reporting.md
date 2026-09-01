# ADR-079: Persist the selected trial for reporting

- **Status:** Accepted
- **Date:** 2026-08-30
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Extends:** ADR-071 (preserve selected calibration finalist)
- **Finding:** `docs/findings/FINDING-015-pool-report-reconstructs-the-wrong-finalist.md`

## Context

ADR-071 made calibration use the same in-memory selection rule as `run_search`, but the persisted
real experiment retains only `best_strategy_name`. Pool reporting still reconstructs max DSR.
Names cannot repair this: refinement can append a second trial from the same strategy family.

## Decision

1. New `Experiment` rows persist `selected_trial_index`, the position sent to holdout and gate.
2. One pool-report helper resolves that index for every finalist-level statistic and attribution.
3. The helper refuses an out-of-range index or disagreement with `best_strategy_name`.
4. Legacy rows keep `selected_trial_index=None` and retain max-DSR reconstruction. Existing default
   artifacts are therefore semantically unchanged; no historical identity is invented.
5. No gate, threshold, search choice, or generated artifact changes.

## Consequences

Future non-default real-pool reports describe the same family as their verdict and calibration.
The field is an immutable list position, so duplicate family names from refinement are unambiguous.
Old non-default rows would remain unknowable, but none were committed.

## Reversal

Remove `selected_trial_index` and restore unconditional max-DSR reporting. That restores
FINDING-015 for every non-default production experiment.
