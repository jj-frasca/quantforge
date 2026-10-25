# ADR-369: Bind leaderboard rows to the persisted selected trial

- **Status:** Accepted
- **Date:** 2026-10-25
- **Deciders:** Codex autonomous session32, ISO2026-W43
- **Resolves:** FINDING-309
- **Extends:** ADR-018/079/147

## Context

rank_experiments reconstructs the highest-margin trial even when ADR-079 records
a different selected trial. Its row combines the unselected strategy and margin
with the selected graduate's holdout and verdict. Canonical model construction
and JSON reload accept the coherent source experiment; the projection loses its
identity. Same-family refinement makes matching only a strategy name insufficient.
Independent research review confirmed cross-family and same-family witnesses.

## Decision

For each nonempty experiment, replace the within-experiment max-margin choice
with existing selected_trial(exp). Update the function documentation to identify
the represented finalist. Preserve the helper's index-based identity, legacy
max-margin fallback and existing identity errors. Do not reconstruct whole
experiment graphs or introduce a new validation boundary.

Keep the current across-experiment ordering key (graduated, margin), per-symbol
collapse, sorted output, empty-trial skip, unique-symbol universe count,
holdout/bar calculation, value score and public fields. The margin in that key
now belongs to the represented selected trial. When prior ranking used another
trial's margin, a different experiment for that symbol may win and consequently
its existing holdout annotation may be represented. No threshold changes.

No search, selection rule, gate, scientific estimator, accounting-v14 fingerprint,
calibration procedure, generated file or frozen cohort changes. This is a
reporting repair; no affected historical record or false graduate is established.

## Alternatives and tradeoffs

- Match best_strategy_name: cannot disambiguate refinement trials.
- Show max margin as a separate statistic: adds public fields and still requires
  correcting the graduate identity; unnecessary for this repair.
- Revalidate every experiment at projection: broader graph validation and cost,
  outside the canonical source identity issue demonstrated here.
- Preserve erroneous cross-experiment winners: would require ranking by an
  unrelated statistic; retain the policy while correcting its source operand.

## Verification and reversal

Observe failing regressions before source edits: cross-family and same-family
selection, graduated and nongraduated records, JSON/store/HTTP projection,
per-symbol winner changes and pool-summary consequences. Hypothesis checks
selected identity and margin across valid finite margins and trial orders.
Pin ordinary selected-is-max and legacy payloads, empty behavior, universe and
holdout evidence and source nonmutation. Require independent final review,
foreground make check-all, individual publication and exact CI verification.

Restore the max-margin choice and former wording to reverse, reopening F309.
Preserve original generated records and all evidence.
