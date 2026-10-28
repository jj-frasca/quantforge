# ADR-394: Compose expanding SMA research windows

- **Status:** Accepted
- **Date:** 2026-10-28
- **Deciders:** Codex autonomous session12, ISO2026-W44
- **Relates:** ADR-048/293/391/392/393; FINDING-332 remains open

## Context

ADR-392/393 isolate train-only SMA adaptation and one native-metric forward
continuation. Compose those reviewed operations across existing expanding split
geometry before considering production integration or a fixed-grid comparison.
ADR-393 is published and exact CI-green; prospective research review approved
this bounded contract before source or test adoption.

## Options Considered

1. **Unused expanding composition (chosen).**
   - Pro: measures repeated train-only adaptive construction with paired windows.
   - Con: extra engine work; no production, calibration or improvement evidence.
2. **Integrate into production WF immediately.**
   - Pro: would expose nested adaptation in existing reports.
   - Con: changes statistic/identity and needs separate integration and matched
     calibration governance; native SMA scoring is not production WF parity.
3. **Add fixed-grid controls and effect estimates now.**
   - Pro: could quantify differences on a supplied example.
   - Con: control identity, parameter counts and comparison arithmetic deserve
     separate design; no advantage is established by this composition alone.

## Decision

Add unused `evaluate_sma_expanding_windows` in `lab/sma_walk_forward.py`. Accept
caller-declared search-side prices, original n_splits/min_train and the explicit
ADR-392 selection settings. Use existing walk_forward_splits(len(frame), ...)
directly, retaining its original nonboolean Integral validation and geometry.
Generate all splits before engine work; accept no arbitrary split arrays.
Normalize generated exclusive endpoints to Python integers. Call ADR-393 once
per window with identical explicit settings and a **per-window budget**.

Validate prices through each window's used prefix, without a whole-frame price
prepass. The final test block reaches len(frame), so aggregate success validates
every input row. An invalid later prefix can abort after earlier engine work;
no partial aggregate, dropped window or zero replacement is returned.

Return a frozen primitive result with n_obs, tuple windows, paired equal means
and method `nested-sma-native-metrics-expanding-v1`. Define each native mean as
math.fsum(score/K for score in window_scores), with a finite-result check and
arithmetic failures propagated. This is a stated binary64 recipe, not exact-real
averaging or production WF arithmetic parity. Add no efficiency, consistency,
stitched returns or other summaries.

Counts sum actual window hypotheses and physical calls, preserving repeated
parameters across windows. On success calls=H+K, where K is the window count;
the total can exceed the per-window budget. These are local compute counts,
not a single budget-limited production search or lifetime/DSR denominator.

## Consequences and verification

This supplies one research diagnostic for the declared single-SMA procedure.
Each config's historical state and internal costs continue into its test block;
no account switching, flat start, benchmark turnover model or executable stitched
policy is claimed. Caller search/holdout boundaries, acquisition, provenance and
PIT remain uncertified. No production caller, persisted artifact, source/cohort
execution, threshold, gate, fingerprint, v14 or generated evidence changes.
F332 remains open for production adaptive evaluation; no prevalence, improvement,
false graduate or calibration-rate conclusion follows.

TDD before implementation: direct ADR-393 window oracles, exact shared splitter
geometry, paired averaging and actual engine calls; singleton and active-refined
cases; per-window versus total budget; original invalid counts before engine work;
later-prefix and arithmetic failures without partial output; immutable evidence.
Hypothesis checks early-window independence under later valid-price changes and
paired mean bounds on controlled data. Run independent research review, existing
selector/window regressions and foreground make check-all, then individually
publish with safe synchronization and exact CI verification.

Reversal removes this unused module, tests and cold contract. Preserve this ADR
and F332; no current producer or stored artifact requires migration.
