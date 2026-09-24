# ADR-125: Drive the strategy-builder smoke test off the catalog, not a hand-maintained list

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** Claude autonomous session 104
- **Resolves:** FINDING-053

## Context

`test_build_strategy_dispatches_each_config_variant` claims to be the backstop for ADR-010's
promise that every catalog strategy is constructible, but its body was a hardcoded literal list of
config instances that stopped growing after the 11th strategy while 23 more were added to
`STRATEGY_CATALOG`. The test's name and comment no longer matched what it actually checked.

## Options Considered

1. **Iterate `STRATEGY_CATALOG` directly, calling `build_strategy_from_dict(entry.name, {})` for
   each entry.**
   - Pro: automatically stays exhaustive as strategies are added — the same fix shape as any other
     "a list drifted out of sync with its source of truth" bug. Relies on each config's defaults
     being valid, which `test_strategy_catalog_consistency.py` already separately asserts for every
     entry, so this doesn't need to re-prove that.
   - Con: exercises `build_strategy` only indirectly (through `build_strategy_from_dict`'s
     validate-then-dispatch), not `build_strategy` called with a hand-built config object directly —
     acceptable, since `test_build_strategy_returns_the_right_concrete_class` already covers that
     direct path for one representative config.
2. **Import `_CONFIG_FOR_NAME` from `test_strategy_catalog_consistency.py` and instantiate each
   config class directly.**
   - Con: couples this test file to another test module's private-looking mapping; the catalog
     itself is already the more natural single source of truth to iterate.
3. **Extend the hardcoded list to cover all 34 current entries.**
   - Con: reintroduces the exact defect this ADR fixes — the list would go stale again the next time
     a strategy is added, with nothing forcing it to grow.

Chose option 1: iterating the catalog directly is both the smallest diff and the one that can't
silently fall behind again.

## Decision

Replace the hardcoded 11-item list in `test_build_strategy_dispatches_each_config_variant` with a
loop over `STRATEGY_CATALOG`, calling `build_strategy_from_dict(entry.name, {})` for each entry.

## Consequences

- The smoke test now exercises all 34 current strategies' dispatch branches and will automatically
  cover any future strategy added to the catalog, with no further test maintenance required.
- No production code changed.

## Reversal

Revert to a hardcoded list. Not recommended — reintroduces FINDING-053's silent staleness.
