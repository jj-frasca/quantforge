# ADR-122: Make the in-memory repository's `save_bars` idempotent

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** Claude autonomous session 104
- **Resolves:** FINDING-050
- **Related:** ADR-118 (fixed within-call duplicates; this fixes cross-call duplicates in the same
  backend)

## Context

`InMemoryPriceBarRepository.save_bars` appended every bar to a plain per-symbol list. Production's
`TimescaleDBPriceBarRepository.save_bars` upserts on `(symbol, timestamp_utc, source)`. The two
`PriceBarRepository` implementations therefore disagreed on repeat-save behavior, and the
cache-aside re-ingest path (`_load_frame` in `backtest.py`/`validation.py`) can call `save_bars`
more than once for overlapping ranges in ordinary use, silently duplicating bars in the in-memory
backend (the local/dev default) and double-weighting them in any frame built from that store.

## Options Considered

1. **Key the in-memory store by `(timestamp_utc, source)` per symbol, matching the production PK.**
   - Pro: makes the two Protocol implementations agree on the same primary key, by construction —
     the same fix shape as any other PK-mismatch bug. Minimal diff (dict instead of list).
   - Con: `get_bars` must read `.values()` instead of iterating the list directly (trivial change).
2. **Deduplicate at read time in `get_bars` instead of write time.**
   - Con: leaves the store holding unbounded duplicate rows internally (memory growth on repeated
     re-ingestion) and picks an implicit "last write wins" or "first write wins" policy at read time
     that isn't obviously equivalent to production's upsert-at-write semantics.
3. **Leave it alone; treat the in-memory repository as "not for production" per its own docstring.**
   - Con: it is still the default backend for local dev and every unit/API test that doesn't use the
     Timescale integration fixtures — divergent behavior there means a bug can look absent locally
     and only appear once a change reaches the Timescale-backed path, the opposite of what a fast,
     representative dev backend should do.

Chose option 1: fixes the primary-key mismatch directly, at the point it exists, mirroring how
production already resolves it.

## Decision

`InMemoryPriceBarRepository._bars` changes from `dict[str, list[PriceBar]]` to
`dict[str, dict[tuple[datetime, str], PriceBar]]`, keyed per symbol by `(timestamp_utc, source)`.
`save_bars` assigns into that dict (overwrite semantics) instead of appending to a list. `get_bars`
reads `.values()` instead of the list directly; its existing filter-then-sort logic is unchanged.

## Consequences

- `InMemoryPriceBarRepository.save_bars` is now idempotent on the same
  `(symbol, timestamp_utc, source)` key, matching `TimescaleDBPriceBarRepository` exactly.
- The cache-aside re-ingest path (`_load_frame`) can no longer silently duplicate bars in the
  in-memory backend for overlapping-range requests.
- `test_save_bars_is_idempotent` now exists for both `PriceBarRepository` implementations, closing
  the test-coverage asymmetry FINDING-050 identified.

## Reversal

Revert `_bars` to `dict[str, list[PriceBar]]` and `save_bars` to a plain append. Not recommended —
reintroduces FINDING-050's divergence between the two repository implementations.
