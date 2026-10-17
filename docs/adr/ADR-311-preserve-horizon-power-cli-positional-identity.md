# ADR-311: Preserve horizon power CLI positional identity

- **Status:** Accepted
- **Date:** 2026-10-17
- **Deciders:** Codex autonomous session 28, ISO 2026-W42
- **Resolves:** FINDING-263
- **Extends:** ADR-042/053/307

## Context

ADR-307 repaired AR power command parsing, but the separate horizon driver still
removes positional tokens by comparing their text to option values. A requested
seed equal to --n-bars becomes zero; an output path equal to the count or seed can
change the requested number of sources or seeds. Public-main mock reproductions
establish the bug without drawing data, scoring a reference or running a search.
The driver prints its parsed inputs; no affected historical cohort, false
persisted headline, altered power rate or false graduate is established.

## Options considered

1. Apply ADR-307's local value-position registry to this driver. Narrow,
   reversible and preserves existing source/scoring/report calls.
2. Replace both parsers with a shared argparse abstraction. Changes more policy
   and unrelated callers than needed; deferred.
3. Restrict count/seed values to avoid collisions. Invents a source domain and
   leaves ambiguity; rejected.

## Decision

Exclude every token immediately after a known value option by its argv position,
not all tokens with the same text. Register --out, --half-life, --deviation-share
and --n-bars. Keep existing option-token filtering and positional order. Repeated
options retain first-occurrence lookup while all their values are excluded from
positionals. Future value flags must join the registry.

Preserve _flag, missing/unknown flag and empty-value truthiness policy, integer
and float parsing, defaults, symbols, seed+i, strategy catalog, output behavior,
generator/scorer/measurement/report calls and all source/reference calculations.
Do not add sharding, method attribution, new argument domains or parser syntax.
No threshold, search/gate identity, v14, workflow or generated record changes.
Residual F159 report claims remain a separate reporting slice.

## Verification and reversal

Write and observe RED public-main tests before runtime edits. Mock generators,
all three reference scorers, measurement and reporting; output only to fresh test
scratch paths. Cover count/seed/history/output/half-life/share collisions,
interleaving, repeats, defaults, ordinary controls and exact downstream calls.
No source draw, search or frozen-cohort operation is needed or authorized.

Independently preserve every original AST operation except positional extraction,
keep all existing tests unchanged, run full foreground make check-all, explicitly
commit/publish the unit and verify exact master CI. Restore text filtering to
reverse this parser change and reopen F263. Never retry, redraw, relabel or rewrite
historical evidence to compensate for this defect.
