# ADR-009: Storage access pattern (sync ingestion vs async)

- **Status**: Proposed (awaiting ratification — see "Open question")
- **Date**: 2026-05-28
- **Deciders**: Joe Frasca (pending)

## Context
ADR-002 chose FastAPI + "SQLAlchemy 2.0 async", and CLAUDE.md forbids sync DB calls inside
async routes. But two facts complicate a blanket "async everywhere":
- The **ingestion pipeline is a batch job**, not a request handler, and **yfinance is a
  synchronous, blocking library** — an async pipeline must push the fetch to a thread.
- The current `DataIngestionPipeline` and `PriceBarRepository` Protocol are **synchronous**
  (built that way for the in-memory store, which needs no I/O).

We must decide how the concrete TimescaleDB repository and the API read path access the DB.
This was deferred so it could be made deliberately rather than guessed at build time.

## Options Considered
1. **Async everywhere (asyncpg).** Make the repository Protocol and the ingestion pipeline
   async; run the blocking yfinance fetch via `run_in_executor`.
   - Pro: one driver (asyncpg), one session style; fully matches the ADR-002 async stance;
     API reads are naturally async.
   - Con: requires refactoring the just-built sync pipeline + in-memory repo to async;
     ingestion gains executor plumbing for a job that doesn't need concurrency.
2. **Split: sync batch ingestion (psycopg) + async API reads (asyncpg).**
   - Pro: ingestion stays simple and matches sync yfinance; API request path is async per
     spec; each path uses the session style that fits it.
   - Con: two drivers and two engine/session setups to maintain; ORM models shared but
     accessed two ways.
3. **Sync everywhere (psycopg), including API routes.**
   - Pro: simplest; one driver; no refactor.
   - Con: violates the spec — sync DB calls block the event loop in async FastAPI routes.
     Rejected.

## Decision (proposed)
**Lean Option 1 (async everywhere).** Single driver (asyncpg), spec-aligned, and the
ingestion pipeline becoming async is a contained change (the in-memory repo's methods become
`async` no-ops; `fetch_price_bars` runs in an executor). This keeps one mental model for all
DB access and honors the async API requirement without a second driver.

## Open question (for ratification)
Confirm Option 1 vs Option 2 before the concrete TimescaleDB repository + Alembic migration
are built. If Option 1: the sync `PriceBarRepository`/`DataIngestionPipeline` (commit 8afca88)
are refactored to async. If Option 2: they stay sync and a separate async read repository is
added for the API. Either way the ORM models (ADR-on-schema, commit 8b8b8ef) are unaffected.

## Consequences
- The concrete repository, Alembic migration (incl. `create_hypertable`), and DB round-trip
  tests are **Docker-gated** and excluded from CI (`make test` skips `integration`), run via
  `make test-integration` locally. (Mirrors the live-data test handling — ADR-006/§0.5.)
- Whichever option, downstream callers still gate on `DataQualityReport.passed` (ADR-006).
