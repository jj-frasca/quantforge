# ADR-134: Bind cached price-bar reads to the active adapter source

- **Status:** Accepted
- **Date:** 2026-09-26
- **Deciders:** Codex autonomous session 26 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-065
- **Extends:** ADR-005 and ADR-118

## Context

ADR-118 ensures one ingestion batch contains one source matching its adapter, but canonical storage
keys bars by `(symbol, timestamp_utc, source)` and repository reads omit source. Durable storage can
therefore contain yfinance and Alpaca observations for the same symbol/calendar. After a runtime
adapter change, cache-aside code may silently reuse the prior vendor; after both are stored, reads
may construct a duplicated mixed-vendor research frame.

## Options Considered

1. **Require source on every price-bar repository read.**
   - Pro: makes cache identity match acquisition identity; a different vendor is an ordinary cache
     miss; prevents duplicate mixed-vendor calendars at the storage boundary.
   - Con: every read caller must know the active adapter source.
2. **Delete or replace rows from other sources during ingestion.**
   - Pro: preserves the existing repository interface.
   - Con: destroys potentially useful vendor evidence and makes a configuration change mutate
     unrelated historical records.
3. **Read all sources and choose or deduplicate downstream.**
   - Pro: avoids an interface change.
   - Con: invents a hidden vendor-precedence policy after the quality report and permits research
     code to observe a non-unique calendar before selection.

## Decision

Add required source identity to `PriceBarRepository.get_bars`. Both in-memory and TimescaleDB
implementations filter by normalized symbol, exact source, and half-open `[start, end)` range.
Cache-aside research loads pass `adapter.source`; a cache populated only by another adapter is a
miss and the normal ingestion pipeline fetches the active source. `GET /api/v1/bars` also depends on
the active adapter and returns only its source's cached projection.

Do not delete other-vendor rows and do not add a fallback across sources. Cross-vendor comparison
remains a separate explicit operation. No data-quality heuristic, search rule, gate, or validation
threshold changes.

## Consequences

- Every returned research frame has one source selected before construction.
- Runtime adapter changes cannot silently reuse another vendor's cache.
- Multiple vendors may coexist durably for future explicit cross-validation without accidental
  mixing in ordinary reads.
- Repository test doubles and callers must carry the same source identity as production.

## Reversal

Remove the source parameter and filters. That would restore configuration-dependent cache reuse and
mixed-vendor calendars, so reversal is not recommended.
