# FINDING-093: Trial and graduate claims are mutable and can carry invalid evidence

- **Severity:** High — shared methodology records can drift or serialize evidence they never validly measured
- **Status:** Resolved by ADR-162
- **Date:** 2026-10-04
- **Affects:** ADR-014, ADR-016, ADR-046, ADR-054, ADR-104, ADR-147, and ADR-160

## Finding

`Trial` and `Graduate` declare `frozen=True`, but both retain their caller-owned `parameters`
dictionaries. A caller can therefore change strategy identity after construction and serialize a
different claim under the same surrounding experiment identity. Direct `Trial` construction also
accepts an empty strategy name, non-finite parameter and diagnostic values, PBO and stability
outside `[0, 1]`, and a probability-form DSR outside `[0, 1]`. Direct `Graduate` construction
accepts the same mutable/non-finite strategy identity, a failed gate, non-finite holdout evidence,
negative holdout length, and structured holdout values that disagree with its nested gate result.
NaN and infinity serialize as JSON `null`.

ADR-147 defensively reconstructs and relates these leaves when they are attached to a single-name
experiment, and ADR-145 does the same for cross-sectional experiments. That does not make the
shared models valid at direct construction, during search repricing, or in consumers that use them
before attachment. Both search paths currently create repriced trials through validation-bypassing
`model_copy(update=...)`.

A read-only compatibility audit found all 116,919 trial-shaped records and all 250 graduates in
committed `data/*.json` compatible with the proposed finite/range/identity invariants. Every
committed graduate has a passing gate, matching structured holdout evidence, and at least 252
holdout bars.

## Required correction

Make `Trial` and `Graduate` defensive, self-validating shared claims. Preserve their JSON object
shapes while freezing parameter mappings; require non-empty strategy identity and finite numeric
parameters/statistics; bind PBO, stability, and probability DSR to their mathematical ranges; and
require a graduate's passing gate, positive holdout length, finite wealth-preserving return, and
exact structured holdout agreement. Reconstruct repriced trials through validation instead of
unchecked model copies. Do not change any statistic, selector, gate predicate, threshold, search
budget, workflow, or generated record.
