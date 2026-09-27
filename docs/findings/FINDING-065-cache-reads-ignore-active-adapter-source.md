# FINDING-065: Cache reads ignore the active market-data adapter

- **Severity:** High
- **Status:** Resolved by ADR-134
- **Found:** 2026-09-26, Codex autonomous session 26
- **Affects:** `PriceBarRepository`, cache-aside research APIs, `GET /api/v1/bars`

## Finding

ADR-118 binds each ingestion batch to exactly one adapter source, but repository reads filter only
by symbol and timestamp range. The storage primary key deliberately permits the same symbol and
timestamp from different sources. Consequently, a cache warmed under yfinance is accepted as a
complete hit after the configured adapter changes to Alpaca, so the requested adapter is never
called. If both sources have been stored, one repository read returns both observations for each
overlapping timestamp and downstream research receives a non-unique calendar.

The quality gate cannot prevent this cross-request mixture: it validates one ingestion batch at a
time, before storage. Adapter selection is runtime configuration, while TimescaleDB is durable
across configuration changes. The in-memory repository has the same behavior, so tests and
production agree on the defect rather than protecting against it.

## Required correction

Make source part of every price-bar read identity. Cache-aside research paths and the read-only bars
endpoint must request only the active adapter's source. Both repository implementations must filter
on symbol, source, and the half-open UTC range. A cache containing another vendor must be a miss,
then ingestion may populate the active source normally. No quality heuristic or validation
threshold changes.
