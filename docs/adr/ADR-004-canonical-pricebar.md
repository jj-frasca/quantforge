# ADR-004: Canonical PriceBar schema, normalized at ingestion

- **Status**: Accepted
- **Date**: 2026-05-27
- **Deciders**: Joe Frasca

## Context
Data arrives from multiple vendors (yfinance now; Polygon in Phase 3) with different field
names, types, timezones, and adjustment conventions. Every downstream component — research,
backtesting, validation — must see one consistent shape, or subtle bugs (timezone mixing,
double-applied split adjustments) will corrupt results in ways that are hard to trace.

## Options Considered
1. **Canonical `PriceBar` schema; normalize once at ingestion.**
   - Pro: downstream code depends on exactly one contract; normalization logic lives in one
     place and is tested once; storage holds clean, query-ready data.
   - Con: ingestion does more work; adding a vendor means writing a normalizer.
2. **Normalize at query time (store raw vendor rows, convert on read).**
   - Pro: storage mirrors the source exactly.
   - Con: every read path re-implements normalization; easy to diverge; repeated CPU cost;
     timezone/adjustment bugs surface far from the data.
3. **Store raw only, normalize ad hoc in each consumer.**
   - Con: worst of both — no single contract, guaranteed drift between consumers.

## Decision
Define a **canonical `PriceBar`** (symbol, `timestamp_utc`, OHLC as `Decimal(18,6)`
split/dividend-adjusted, volume, `adj_factor`, source, `quality_flags`) and **normalize at
ingestion, never at query time.** Timestamps are coerced to UTC at ingestion as a hard
enforcement (failure raises `ValidationError`), not a soft flag.

## Consequences
- All consumers import one model; no consumer re-derives normalization.
- `adj_factor` is applied exactly once at ingestion — applying it again downstream is a bug
  (prices come out 2× wrong); this is called out in the data-engineer agent spec.
- Prices use `Decimal`, never `float`, to round-trip exactly (`.claude/rules/backend-python.md`).
- Adding a vendor = implementing its normalizer to emit `PriceBar` (see ADR-005); no
  downstream change.
- Full field definitions and SQL live in `.claude/context/data-contracts.md`, written
  before the schema at the start of Phase 2.
