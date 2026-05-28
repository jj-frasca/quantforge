# ADR-003: TimescaleDB for time-series storage

- **Status**: Accepted
- **Date**: 2026-05-27
- **Deciders**: Joe Frasca

## Context
OHLCV data is time-series at its core: many symbols, long histories, queried by symbol
and time range. We need efficient range scans and time-bucketing, but we also want
ordinary SQL, relational joins to fundamentals/experiments, and no proprietary lock-in.

## Options Considered
1. **TimescaleDB (PostgreSQL extension, hypertables).**
   - Pro: full PostgreSQL — standard SQL, joins, transactions, the async `psycopg`/asyncpg
     drivers; hypertables give automatic time partitioning and fast range queries;
     continuous aggregates available later; no new query language to learn.
   - Con: must run the Timescale image rather than vanilla Postgres; an extension dependency.
2. **InfluxDB.**
   - Pro: purpose-built TSDB.
   - Con: Flux/InfluxQL lock-in; awkward relational joins to fundamentals and experiment
     metadata; a second data model to maintain.
3. **Vanilla PostgreSQL (plain tables + btree on (symbol, ts)).**
   - Pro: simplest; no extension.
   - Con: manual partitioning as data grows; loses hypertable ergonomics and time-series
     query optimizations.
4. **Parquet files on disk (DuckDB/Polars over them).**
   - Pro: cheap, columnar, great for batch research.
   - Con: no concurrent writes / serving story; weak for the API's point/range queries and
     for relational experiment lineage.

## Decision
**TimescaleDB hypertables** for OHLCV (and time-series fundamentals). Relational tables in
the same Postgres instance hold experiment manifests, quality reports, and fundamentals.

## Consequences
- Queries MUST filter by `symbol` AND a `timestamp` range — omitting either triggers a full
  hypertable scan that will time out on multi-year data (encoded in the data-engineer agent
  spec and data-contracts.md when written).
- We stay in SQL; joins between prices, fundamentals, and experiment lineage are trivial.
- Local dev runs the `timescale/timescaledb` image via docker-compose; the exact tag is
  pinned in Phase 2 once the schema lands.
- Migrations are managed with Alembic (`make migrate`).
