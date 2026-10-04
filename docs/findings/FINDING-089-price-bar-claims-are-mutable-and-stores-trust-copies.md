# FINDING-089: Price-bar claims are mutable and stores trust copies

- **Severity:** High — canonical market observations can change or bypass invariants after validation
- **Status:** Resolved by ADR-157
- **Date:** 2026-10-03
- **Affects:** ADR-004 canonical bars and ADR-122 repository parity

## Finding

`PriceBar` declares `frozen=True`, but its `quality_flags` dictionary and any nested list/dictionary
remain mutable and retain caller aliases. A validated canonical observation can therefore serialize
different evidence later under the same `(symbol, timestamp_utc, source)` identity. The JSONB field
also accepts arbitrary Python objects and non-finite nested floats, failing late or changing shape at
serialization/database boundaries.

Both repository implementations trust instantiated bars. Pydantic's unchecked
`model_copy(update=...)` can bypass symbol, timestamp, OHLC, volume, source, and flag validation.
The in-memory writer retains such objects directly and mutates its store one bar at a time; an
invalid later row can therefore leave a partial batch if validation is added only inside that loop.
The TimescaleDB writer likewise opens a session before establishing that the complete batch is one
valid canonical-bar collection.

## Required correction

Make `PriceBar` one defensive JSON-safe model boundary: recursively copy/freeze `quality_flags` and
accept only string-keyed JSON objects with finite leaves. Both writers must reconstruct every bar in
the batch before mutating memory or opening a database session, preserving order, last-write-wins
upsert semantics, canonical primary-key identity, all OHLC rules, and the existing JSON object shape.
No quality heuristic, threshold, adjustment formula, SQL schema, or committed data changes.
