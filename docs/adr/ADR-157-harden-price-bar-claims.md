# ADR-157: Harden canonical price-bar claims

- **Status:** Accepted
- **Date:** 2026-10-03
- **Deciders:** Codex autonomous session 22 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-089
- **Extends:** ADR-004, ADR-122, ADR-150, ADR-156

## Context

ADR-004 makes `PriceBar` the single canonical observation consumed by storage, quality checks, and
research. Model-level freezing does not protect nested `quality_flags`, and repository writers trust
model instances even though unchecked Pydantic copies bypass every constructor invariant. One
canonical key can therefore retain or persist a contradictory observation, and a memory batch can
partially apply if validation happens only while writing.

## Options Considered

1. **Deep-freeze at the model and prevalidate whole batches at both repositories.**
   - Pro: every adapter, API, quality, storage, and research path shares the same canonical boundary;
     batch rejection is atomic before external state.
   - Con: requires a small reusable immutable JSON-value helper in the data-model layer.
2. **Copy or serialize only inside repositories.**
   - Pro: protects stored snapshots.
   - Con: callers and quality checks still observe mutable bars, and unsupported values fail late.
3. **Remove `quality_flags` because quality reports now carry audit evidence.**
   - Pro: eliminates the mutable field.
   - Con: changes ADR-004 and the SQL schema without proving the compatibility cost is justified.

## Decision

Recursively copy and freeze `quality_flags`, accepting only JSON-compatible null, boolean, string,
integer, and finite-float leaves with string mapping keys. A shared data-model helper provides the
same immutable JSON object/array behavior used by quality-issue context; explicit Pydantic field
serializers preserve ordinary JSON shapes.

`InMemoryPriceBarRepository.save_bars` and `TimescaleDBPriceBarRepository.save_bars` reconstruct
the complete incoming batch through `PriceBar` before touching retained state or opening a session.
Only then do they preserve the existing input order, primary-key overwrite/upsert behavior, and
return count.

## Consequences

- Canonical identity, OHLC values, and flags cannot drift after validation.
- Invalid unchecked copies reject the whole batch before memory or database state access.
- Flags remain JSON objects/arrays; `None` continues to mean no bar-level flags.
- No data-quality check, warning threshold, adjustment formula, SQL schema, or existing key changes.

## Reversal

Restore mutable flag containers or trust instantiated bars at repository writes. That would reopen
FINDING-089 and is not recommended.
