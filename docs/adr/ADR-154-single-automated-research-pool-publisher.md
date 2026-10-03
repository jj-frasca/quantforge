# ADR-154: Use one automated research-pool publisher

- **Status:** Accepted
- **Date:** 2026-10-02
- **Deciders:** Codex autonomous session 21 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-084
- **Extends:** ADR-026, ADR-030, ADR-032, and ADR-152

## Context

Daily discovery and the weekly scheduled hunt both run the same strategy catalog and gate over
overlapping universes, then publish the same per-symbol pool partitions from independent,
hours-old checkouts. The local `cron_hunt.sh` fallback performs the same mutation and commits with
an unreconciled push. Per-symbol storage removes races among disjoint shards; it cannot reconcile
two runs that update the same symbol.

The weekly job is redundant. The daily discovery universe contains all 503 S&P symbols plus 108
additional liquid instruments, and the sharded workflow searches that superset on every weekday.
Daily discovery also already accepts a manually selected universe file.

## Decision

- `Daily discovery (sharded)` is the sole automated workflow that stages and publishes
  `data/research_pool`.
- Remove the redundant scheduled-hunt workflow rather than attempting to serialize two equivalent
  publishers with GitHub's lossy concurrency queue.
- Remove the local committing/pushing hunt fallback. The underlying Python hunt driver remains
  available for deliberate local research, subject to the existing rule that sessions do not
  commit generated `data/*.json` output.
- Preserve daily discovery's schedule, sharding, full catalog, gate, committed-pool prior, artifact
  consolidation, manual universe input, and retry behavior unchanged.
- Enforce the publisher boundary with a static repository contract and the universe-superset fact
  with a data-independent filename-set assertion.

No workflow is dispatched and no existing research evidence, gate, trial count, retention limit,
or validation threshold changes.

## Consequences

- Automated research publication has one workflow-owned commit boundary, eliminating cross-workflow
  JSON rebase conflicts and the divergent local-push failure mode.
- Scheduled coverage does not shrink: the former weekly S&P run was a subset of the weekday daily
  discovery run.
- Custom or recovery sweeps use daily discovery's manual input and therefore share its workflow
  concurrency boundary.
- A manually invoked local hunt may still write a local pool for inspection, but no repository
  automation commits or pushes it.

## Options considered

1. **Use one shared concurrency group.** Rejected because GitHub retains at most one pending member;
   a newer run can replace a pending requested sweep.
2. **Merge after every rejected push.** Rejected because generated JSON conflicts require a
   domain-aware artifact merge, and the duplicate weekly search provides no unique coverage worth
   that extra publication path.
3. **Keep only the weekly hunt.** Rejected because it covers a smaller universe less frequently and
   gives up ADR-026's parallel sharding.

## Reversal

Restore the scheduled-hunt workflow and local wrapper from history. That reopens FINDING-084 unless
they publish through a lossless, domain-aware merge boundary owned by the daily discovery workflow.
