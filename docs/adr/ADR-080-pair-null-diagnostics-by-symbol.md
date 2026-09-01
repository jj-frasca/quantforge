# ADR-080: Pair null diagnostics by searched symbol

- **Status:** Accepted
- **Date:** 2026-09-01
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Acts on:** ADR-068 (walk-forward excess), ADR-078 (purged-CV excess)
- **Relates to:** ADR-037 (sharded null calibration), ADR-067 (absent is not zero),
  ADR-071 (preserve selected calibration finalist)
- **Finding:** `docs/findings/FINDING-016-null-diagnostics-lose-symbol-pairing.md`

## Context

The two excess rows are defined per searched symbol: finalist OOS Sharpe minus what holding that
same generated series earned on the same windows or folds. The calibration artifact instead stores
four independent filtered arrays. Length equality is the only pairing guard, but two arrays can
have equal lengths after dropping different symbols. Shard concatenation preserves array order, not
the identity of the observations inside it.

Current production calibration supplies every diagnostic for every successfully searched symbol,
so the committed 7,400-bar artifacts have complete arrays and remain valid. The schema nevertheless
cannot state or enforce the pairing on which ADR-068 and ADR-078 depend.

## Decision

1. New null calibrations persist `NullSymbolDiagnostics`: one immutable record per searched symbol
   carrying `symbol`, `n_bars`, `holdout_years`, and nullable walk-forward/purged-CV OOS and hold
   Sharpes.
2. `NullCalibration.symbol_diagnostics` is the canonical pairing identity. New artifacts retain the
   existing list fields as projections for API and historical compatibility, and model validation
   requires every projection to match the paired records exactly.
3. Shard merge requires either paired records on every shard or legacy records on every shard. It
   rejects mixed schema generations and duplicate symbol identities instead of inventing an order.
4. Excess reporting derives pairs from `symbol_diagnostics`. A legacy artifact may use positional
   pairing only when each relevant array has exactly `n_symbols` entries; completeness proves that
   no searched symbol was filtered out. Partial legacy arrays still support their raw diagnostic
   distributions but cannot produce an excess row.
5. Existing generated JSON is not rewritten. The next ordinary ADR-030 workflow refresh will add
   paired records. No threshold, search, gate, raw diagnostic, or current published verdict moves.

## Alternatives considered

1. **Keep the arrays and validate only equal lengths.** Rejected: equal counts do not identify the
   same symbols.
2. **Store two separate `(oos, hold)` tuple lists.** Better locally, but still loses symbol identity
   through sharding and cannot prove uniqueness or completeness.
3. **Reject every legacy artifact.** Rejected: the complete 7,400-bar arrays are safely pairable and
   the 5,400-bar raw distributions remain valid evidence. Compatibility can be strict without
   discarding measurements.
4. **Rewrite committed artifacts locally.** Forbidden by ADR-030 and the Codex charter. The cloud
   sole writer will populate the additive field on its next authorized run.

## Consequences

- A drift-controlled null observation is structurally tied to the symbol that produced both sides.
- Mixed or duplicate shard identity fails during consolidation rather than reaching a report.
- The API remains backward compatible; consumers that need raw distributions keep the existing
  fields, while paired consumers have a first-class record.
- Legacy artifacts with partial arrays become honestly unmeasured for excess rather than silently
  cross-subtracted.

## Reversal

Remove `symbol_diagnostics` and restore positional pairing on equal-length arrays. That intentionally
restores FINDING-016's inability to prove per-symbol identity.
