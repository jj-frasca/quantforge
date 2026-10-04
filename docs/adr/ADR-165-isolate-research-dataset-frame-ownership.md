# ADR-165: Isolate research dataset frame ownership

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Codex autonomous session 28 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-096
- **Extends:** ADR-137, ADR-139, ADR-140, and ADR-164

## Context

A frozen dataclass does not freeze its pandas payload. `ResearchDataset` retains the caller's
frame and returns the same mutable object to discovery, forward scoring, and paper sizing.
Prices and calendar identity can therefore change after quality checks under an unchanged report.

## Options Considered

1. **Capture a private frame snapshot and return independent working copies.**
   - Pro: keeps ordinary pandas consumers and the `frame=`/dataclass replacement interface.
   - Con: allocates a frame at capture and each read; pandas axes need explicit deep copies.
2. **Set numpy buffers read-only.**
   - Pro: avoids copies on read.
   - Con: pandas column/index replacement still permits mutation and buffer handling is brittle.
3. **Fingerprint and revalidate at every consumer.**
   - Pro: exposes drift explicitly.
   - Con: duplicates ownership checks and leaves future consumers vulnerable.

## Decision

Use a descriptor-backed dataclass field to capture a private defensive frame snapshot and expose
an independent copy on every `frame` read. Copy data and both axes explicitly, including datetime
index storage. Preserve the required constructor argument, frozen field assignment, and
`dataclasses.replace` semantics. Validate the captured frame through the existing checks.
The boundary supports canonical numeric OHLCV frames; it does not claim pandas deep-copy semantics
recursively freeze arbitrary Python objects stored inside object-valued cells.

## Consequences

- Source-frame edits and edits to exposed working frames cannot change retained numeric prices or
  calendar/column identity while quality evidence stays constant.
- Consumers retain ordinary writable DataFrames and current acquisition/evidence JSON shapes.
- Each read costs a frame allocation. Current production consumers read once per scoring/search
  boundary; no financial formula, quality rule, threshold, workflow, or generated record changes.
- Direct construction still relies on its supplied passed report; this change does not prove a
  caller-provided frame was checked, nor add a persisted content hash.

## Reversal

Restore the ordinary dataclass frame field. That reopens FINDING-096 and is not recommended.
