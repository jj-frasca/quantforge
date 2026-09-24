# ADR-127: Enforce the half-open range contract in the Alpaca adapter

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** Claude autonomous session 104
- **Resolves:** FINDING-055

## Context

`AlpacaDataAdapter.fetch_price_bars` must return bars for `[start, end)` per `DataSourceAdapter`'s
documented contract. Alpaca's `end` query parameter is inclusive, and `_fetch_bars` sends only the
date portion with no adjustment, so a normal historical-range request can receive a vendor bar dated
on the caller's exclusive `end` boundary — which `DataQualityEngine`'s `range_mismatch` check
(ADR-119, same day) would now reject at ingestion, silently blocking storage for an otherwise-valid
request.

## Options Considered

1. **Filter the adapter's own output to `[start, end)` in `fetch_price_bars`, after normalization.**
   - Pro: enforces the documented contract at the exact method that promises it, regardless of any
     vendor-specific date/inclusivity quirk — doesn't require correctly reasoning about exactly how
     Alpaca's inclusive `end` interacts with date-only truncation across all cases (DST, weekends,
     multi-page responses). Directly unit-testable via the already-injectable `_fetch` — no network
     needed to prove the fix, unlike a fix inside `_fetch_bars` (`pragma: no cover`).
   - Con: silently drops a boundary bar rather than surfacing why — acceptable here, since dropping
     a bar the caller didn't ask for (by the contract's own definition) is exactly correct behavior,
     not a hidden data loss.
2. **Adjust `_fetch_bars`'s `end` parameter sent to Alpaca (e.g. subtract one day) to compensate for
   the vendor's inclusive semantics.**
   - Con: fixes the symptom only inside the untested network glue, at the specific granularity
     (daily bars) this adapter happens to use today; doesn't defend the method's actual contract if
     Alpaca's behavior differs at another timeframe or a future edge case, and can't be exercised by
     the existing injectable-fetcher unit tests the way option 1 can.
3. **Leave it and rely on the caller to pass a slightly-earlier `end`.**
   - Con: pushes a vendor-specific workaround onto every caller of a supposedly vendor-agnostic
     interface — exactly what `DataSourceAdapter`'s abstraction exists to avoid.

Chose option 1: enforces the contract where it's promised, testable without network, robust to
whatever the vendor's exact inclusive/date-truncation behavior turns out to be.

## Decision

`AlpacaDataAdapter.fetch_price_bars` filters its normalized bars to `start <= b.timestamp_utc < end`
before returning, after normalization and before any caller sees them.

## Consequences

- `AlpacaDataAdapter.fetch_price_bars` now honors its documented half-open contract regardless of
  Alpaca's inclusive-`end` API behavior.
- A live Alpaca-backed ingest whose requested range would otherwise have picked up a
  boundary-date bar no longer trips `DataQualityEngine`'s `range_mismatch` check for that reason.
- `_fetch_bars`'s date-only `end` parameter sent to Alpaca is unchanged — the adapter may still
  fetch one extra day's worth of data from the vendor on some requests, then discard it locally;
  negligible cost for a daily-bar adapter.

## Reversal

Remove the filter line. Not recommended — reintroduces FINDING-055's contract violation, now
directly reachable via ADR-119's `range_mismatch` check.
