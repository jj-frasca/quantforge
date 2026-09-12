# ADR-084: Require the panel-null source-history floor before freezing the cohort

- **Status:** Accepted
- **Date:** 2026-09-12
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Acts on:** FINDING-020
- **Extends:** ADR-081

## Context

ADR-081 freezes an equal-symbol real cohort and then fetches one aligned source panel containing
exactly 7,400 complete rows for every symbol. Cohort selection inherited ADR-064's symmetric ±10%
history band. That band makes descriptive comparisons robust to a growing daily pool, but its lower
half admits symbols whose available histories are shorter than the panel the generator must build.

The current committed pool exposes the mismatch before the measurement is spent: 89 symbols match
the configured band and identities, 50 are below 7,400 bars, and only 39 can establish the requested
history from their recorded search length. Preparation intersects all frozen symbols, so one short
history prevents the entire workflow from producing a source archive.

## Options considered

1. **Keep the symmetric band and let preparation fail.**
   - Pro: no change to cohort selection.
   - Con: the authorized measurement is predictably unexecutable and the failure does not identify
     the infeasible symbols until after every source fetch.
2. **Lower the panel target to the shortest selected history.**
   - Pro: preserves all 89 current symbols.
   - Con: changes the pre-registered history after inspecting the pool and invalidates the intended
     7,400-bar comparison.
3. **Require `target_n_bars <= experiment.n_bars <= target_n_bars * (1 + tolerance)`.**
   - Pro: preserves the pre-registered target, retains ADR-064's bounded upper comparison band, and
     removes infeasible real observations before equal-symbol aggregation.
   - Con: narrows the current cohort from 89 to 39 symbols and remains a necessary-but-not-sufficient
     feasibility check because fetched common calendars can still differ.
4. **Add exact source start/end dates to new experiments and wait for a rebuilt cohort.**
   - Pro: provides stronger real-side calendar lineage for a future instrument.
   - Con: does not make the already pre-registered measurement executable now and would delay it
     until enough new retained experiments accumulate.

## Decision

Choose option 3. `select_panel_null_cohort` admits an experiment only when its stated history is at
least `target_n_bars` and no more than the existing upper tolerance. The floor is applied before
resolving finalists, calculating per-symbol medians, and enforcing the fixed 30-symbol minimum.
`prepare_panel_null_source` remains fail-closed on the actual fetched complete-case calendar; the
recorded history is only an early feasibility boundary, not a substitute for source validation.

The target, tolerance, minimum symbol count, equal-symbol estimator, 400-replicate design, gate,
search, and validation thresholds do not change. The panel measurement remains unspent.

## Consequences

- An infeasible below-target symbol cannot enter an immutable panel-null manifest.
- The current eligible cohort becomes 39 symbols, still above the pre-registered floor of 30.
- Boundary symbols with exactly 7,400 bars remain eligible; symbols above the existing +10% limit
  remain excluded.
- A future fetch can still fail on joint-calendar insufficiency, preserving the stronger source
  boundary instead of trusting experiment metadata.

## Reversal

Removing the lower history floor restores FINDING-020. Changing the 7,400-bar target or the
30-symbol minimum requires a separate ADR before the unspent measurement is dispatched.
