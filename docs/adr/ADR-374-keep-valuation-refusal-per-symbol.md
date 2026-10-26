# ADR-374: Keep valuation attachment refusal inside the per-symbol hunt boundary

- **Status:** Accepted
- **Date:** 2026-10-26
- **Deciders:** Codex autonomous session1, ISO2026-W44
- **Resolves:** FINDING-318
- **Extends:** ADR-023, ADR-137, ADR-147, ADR-373

## Context

A valid valuation object can still describe the wrong requested symbol.
Experiment correctly rejects that attachment, but its reconstruction occurs
outside the universe hunt's per-symbol exception handler. Later symbols never
run, no structured result returns, and earlier valid store writes can remain.
Analogous manifest failures already become per-symbol errors. Independent and
parent synthetic probes confirm the difference; no production incidence is known.

## Options Considered

1. **Move existing valuation revalidation into the existing per-symbol try.**
   - Pro: preserves identity rejection and ordinary ordering while reusing the
     current error/continue policy and retaining store-failure propagation.
   - Con: later symbols now run after an invalid attachment; the failed symbol's
     search work is already spent and still produces no persisted experiment.
2. **Validate the score's symbol before acquisition/search.**
   - Pro: avoids spending search work on mismatched evidence.
   - Con: changes ordering and the behavior of mismatched scores that the enabled
     screen would filter; it expands the correction beyond exception scope.
3. **Keep whole-hunt abort and document partial persistence.**
   - Pro: preserves current malformed-attachment behavior with no code change.
   - Con: contradicts the existing per-symbol resilience policy and treats
     analogous manifest and valuation failures inconsistently.

## Decision

Relocate only the existing `if value_score is not None` Experiment.model_validate
block to the end of run_universe_hunt's existing per-symbol try, after manifest
attachment. Keep the same validation, existing catch classes/error text/continue,
provider/screen/acquisition/search order, None behavior, store.add and result
append. Do not suppress store exceptions, substitute None, weaken validators or
change a schema, formula, threshold, default, search identity or generated record.

## Consequences

Invalid attachment becomes that symbol's error and later names continue. Earlier
valid stored rows remain; the invalid row is never stored. This is no atomic
whole-run guarantee or complete attempted-trial ledger. Provider construction
refusals and the separate fundamental-sweep error policy stay. F317 admission
rubric persistence remains open and is not addressed by this control-flow change.

Observe failing synthetic orchestration tests before patching; cover both screen
modes and roster orders, retained valid/absent scores, filtering and store errors.
Replay the frozen20 ordinary complete controls, retain direct identity-rejection
tests, obtain final research review and run foreground make check-all before
individual publication and exact CI verification. Reverse by moving the same
block back outside try, reopening F318 without changing any model contracts.
