# ADR-129: Tolerate a corrupt shard in fundamentals consolidation

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** Claude autonomous session 104
- **Resolves:** FINDING-057

## Context

`consolidate_fundamentals.py` folds every shard `fundamental_sweep.py` produced into one pool file,
via `load_fundamentals_pool(shard_file)` per shard with no error handling. A shard writer killed
mid-write can leave a truncated/invalid JSON file, which raises and crashes the entire
consolidation — losing every other shard's good work for the week, not just the corrupt one.

## Options Considered

1. **Add `load_fundamentals_shard`, a new function in `record.py` that wraps
   `load_fundamentals_pool` and returns `None` (not `[]`, to distinguish "corrupt" from "genuinely
   empty") on `JSONDecodeError`/`ValidationError`; `consolidate_fundamentals.py` skips and warns on
   `None` instead of crashing.**
   - Pro: the new resilience logic is a pure, directly unit-testable function (no `tmp_path`-heavy
     script-level test needed), matching this codebase's existing "pure function does the work, the
     script is thin glue" convention. `load_fundamentals_pool` itself is unchanged — its existing
     callers (which may legitimately want a corrupt MAIN pool file to raise loudly, a much rarer and
     more serious failure than a transient shard truncation) keep today's strict behavior.
   - Con: none identified.
2. **Make `load_fundamentals_pool` itself tolerant (add a `strict: bool` parameter or always
   swallow errors).**
   - Con: would also silently swallow a corrupt MAIN pool file, which is a single canonical
     accumulated-state file, not an ephemeral per-shard artifact — a corrupted main pool is rare and
     serious enough to want a loud failure, not a silent "treat as empty" that could quietly discard
     the whole pool's history on a future write.
3. **Wrap the whole per-shard loop body in a bare `try/except Exception`.**
   - Con: too broad — would also swallow genuine bugs in `merge_fundamental_records` itself, not
     just the specific "this shard's file is corrupt" failure mode this ADR targets.

Chose option 1: narrowest fix, pure and testable, doesn't change behavior for the main-pool read.

## Decision

New `load_fundamentals_shard(path) -> list[FundamentalRecord] | None` in `record.py`: calls
`load_fundamentals_pool`, catches `json.JSONDecodeError`/`pydantic.ValidationError`, returns `None`.
`consolidate_fundamentals.py`'s per-shard loop calls this instead, printing a warning and
`continue`-ing (not raising) on `None`. The consolidation summary line now reports
`skipped/total` shard counts.

## Consequences

- One corrupt shard file no longer crashes the entire weekly fundamentals consolidation; every
  other shard's work is still folded in and committed.
- The consolidation's console output now names which shard(s) were skipped, so a bad shard is
  visible for investigation rather than silently disappearing.
- `load_fundamentals_pool`'s own strict behavior (raises on malformed content) is unchanged for the
  main-pool read and any other existing caller.

## Reversal

Revert `consolidate_fundamentals.py` to call `load_fundamentals_pool` directly per shard, and
remove `load_fundamentals_shard`. Not recommended — reintroduces FINDING-057's single-point-of-
failure across the whole consolidation.
