# ADR-009: Storage access pattern — synchronous, on psycopg3

- **Status**: Accepted (ratified 2026-05-28; supersedes the "async" detail of ADR-002)
- **Date**: 2026-05-28
- **Deciders**: Joe Frasca

## Context
ADR-002 named "SQLAlchemy 2.0 async" as a sensible default. But before building the concrete
TimescaleDB repository we re-examined it against this project's *actual* workload, and the
generic "async is modern" guidance does not fit:
- **Single-maintainer, low-concurrency** research tool — not a high-QPS public API.
- **DB is localhost** (docker-compose TimescaleDB), not a remote/cloud DB across a network.
- **Ingestion is batch + blocking**: yfinance is synchronous.
- **Reads are analytical**: bounded `(symbol, time-range)` scans for backtests/validation, not
  thousands of concurrent small queries.
- Already built **synchronously**: `DataIngestionPipeline`, the `PriceBarRepository` Protocol,
  the in-memory repo, and the `POST /api/v1/validate` handler (a sync `def`).

## Options Considered
1. **Async everywhere** (asyncpg + async ORM/sessions + async routes).
   - Pro: highest raw driver throughput under high concurrency; one driver; matches ADR-002's wording.
   - Con: real complexity tax — no lazy loading, `AsyncSession` is not concurrency-safe, harder
     testing, greenlet bridging, mypy-strict friction; and the blocking yfinance fetch must be
     pushed to `run_in_executor` *anyway*. None of the concurrency upside applies to a localhost,
     low-concurrency, batch workload.
2. **Split** (sync batch ingestion + async API reads).
   - Pro: each path uses a fitting style.
   - Con: two drivers + two engine/session setups to maintain; a permanent cognitive split for
     no real benefit here.
3. **Sync everywhere** (psycopg3 sync driver + SQLAlchemy 2.0 sync ORM + FastAPI `def` routes).
   - Pro: simplest, most maintainable; localhost sync is frequently *faster* than async;
     FastAPI runs `def` handlers in a threadpool, so blocking DB/yfinance work never stalls the
     event loop; **no rework** of code already built; psycopg3 (not psycopg2, not asyncpg)
     supports BOTH sync and async, so individual hot paths can move to async later without
     changing drivers.
   - Con: bounded by AnyIO's ~40-thread pool under extreme concurrency (irrelevant at this scale);
     "looks less modern" (a non-reason).

## Decision
**Option 3 — synchronous everywhere, on the `psycopg` (psycopg3) driver.**
SQLAlchemy 2.0 *sync* engine/sessions; connection string `postgresql+psycopg://…`; FastAPI DB
endpoints are sync `def` (FastAPI threadpools them). The CLAUDE.md rule "no sync DB calls in
async routes" is honored by *not writing async routes for DB work* — sync `def` + threadpool is
the FastAPI-blessed pattern.

This **reverses an earlier draft lean toward async-everywhere.** Current sources changed the
call: async DB wins on *remote* I/O under *high concurrency*; for localhost + low concurrency it
is slower *and* more complex, and FastAPI handles blocking work in a threadpool. See
SQLAlchemy's asyncio caveats, the FastAPI concurrency docs ("async def + blocking driver is
worse than plain def"), and localhost sync-vs-async benchmarks (links below).

## Consequences
- The deferred TimescaleDB repository implements the **sync** `PriceBarRepository` Protocol — so
  the already-built pipeline/repo/in-memory store need **no refactor**. Driver dependency will be
  `psycopg[binary]`; the ORM models (commit 8b8b8ef) are unchanged.
- `.env.example` and `docker-compose.yml` use `postgresql+psycopg://…` (not `+asyncpg`).
- `.claude/rules/backend-python.md` guidance is "DB access is sync; prefer sync `def` routes for
  DB work; never call a blocking driver inside an `async def`."
- The repository + Alembic migration (`create_hypertable`) + round-trip tests stay Docker-gated
  and excluded from CI (`make test-integration`), mirroring live-data handling (ADR-006/§0.5).
- Downstream callers still gate on `DataQualityReport.passed` (ADR-006).
- **Reversible**: because psycopg3 also speaks async, a future high-concurrency public API can
  move specific paths to async sessions without a driver swap — that would be a new ADR.

## Sources
- SQLAlchemy 2.0 asyncio extension (caveats): https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- FastAPI — Concurrency and async/await (sync `def` runs in a threadpool): https://fastapi.tiangolo.com/async/
- Top PostgreSQL drivers for Python (psycopg3 vs asyncpg): https://www.tigerdata.com/learn/top-postgresql-drivers-for-python
- Localhost async-vs-sync benchmark: https://henryonai.github.io/blog/python-async-vs-sync-benchmark
