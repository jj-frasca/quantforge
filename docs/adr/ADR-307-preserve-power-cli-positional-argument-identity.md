# ADR-307: Preserve AR power CLI positional argument identity

- **Status**: Accepted
- **Date**: 2026-10-17
- **Deciders**: Codex autonomous session 25, ISO 2026-W42
- **Resolves**: FINDING-262
- **Extends**: ADR-041/053

## Context

The AR power driver removes positional arguments by matching their text against a
set of option values. A legitimate seed equal to --n-bars is silently discarded.
Mocked argv `2 7400 --n-bars 7400` invokes the generator with seeds 0,1 instead of
7400,7401. `7400 2 --n-bars 7400` executes two fake source generations instead of
the requested 7400, and resets the seed. The script reports its mistaken parsed
values, so there is no established false artifact headline, but the command's
requested source identity and population are not honored.

This was found before adding explicit drift-reference options. No actual source,
search, workflow, generated artifact or frozen cohort was executed or implicated.

## Options Considered

1. **Exclude known option values by their argv positions.**
   - Pro: fixes value collisions with a narrow local extraction change; existing
     defaults, first-option lookup and source/search calls remain.
   - Con: the known value-option list must be extended when adding new flags.
2. **Replace the full parser with argparse.**
   - Pro: standard parsing and richer errors.
   - Con: changes unknown/repeated/missing option policy and exceeds this defect.
3. **Restrict seeds/counts so option values cannot match.**
   - Pro: avoids the examples.
   - Con: invents a nonsensical source domain and leaves the parser ambiguous.

## Decision

Exclude the value token immediately following every known value-option token
(--shard, --out, --phi, --n-bars, --select-by) by argv index, rather than excluding
all tokens whose text matches a value. Retain existing option-token filtering,
_flag/_select_by evaluation and first-occurrence value lookup, positional ordering,
defaults, integer/float parsing and global-index seed/shard arithmetic. Repeated
known options still use the first value; every occurrence's value is excluded from
positionals. Add future value flags to this registry. No argument-domain, source
law, generator/scorer call, statistic, gate, threshold, v14 or workflow change.

## Consequences

Valid count/seed tokens survive when equal to history or output-path values. Tests
must invoke main with mocked generators, search and reporting, proving exact source
counts and seed lists without measuring a cohort. Cover flag interleaving, repeated
options, defaults, selection and shard preservation. This does not add support for
--flag=value, redesign unknown/missing-option handling, or certify historical runs.
Record the finding, review scope, and run foreground make check-all and exact CI.
Restore value-based filtering to reverse, reopening FINDING-262. Never retry,
redraw, relabel or rewrite frozen/generated evidence to compensate for this bug.

---
*ADRs are immutable. To change this decision, write a new ADR that supersedes it.*
