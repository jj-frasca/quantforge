# ADR-032: The research pool is partitioned by symbol

- **Status**: Accepted
- **Date**: 2026-08-18
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Extends**: ADR-016 (the research pool as the unit of accumulated search), ADR-026 (maximum
  token-free discovery)

## Context
`data/research_pool.json` is a single JSON array holding every experiment ever run. It is the
project's scientific record: the DSR/MinTRL penalty denominator is derived from it, so it must be
committed, not regenerated.

On 2026-08-16 the `Scheduled hunt + auto-promotion` workflow went red and **could not push**:

```
remote: error: File data/research_pool.json is 105.06 MB; this exceeds GitHub's file size limit of 100.00 MB
remote: error: GH001: Large files detected.
```

The committed pool is 45 MB / 3,172 experiments / 105,809 trials (~14 KB per experiment, 81% of the
bytes being the trial rows the MinTRL denominator needs). ADR-026's daily discovery adds ~610
experiments per weekday. The file is not near a limit — it is **past** it, and every hunt that
actually fetches data now produces an unpushable repository state. This is a hard outage of the
project's memory, not a capacity warning.

Two further defects fall out of the same shape:

- **`JsonFileExperimentStore.add()` is O(n) in the whole pool.** It reloads and rewrites all 45 MB
  for every single experiment. A 61-symbol shard rewrites the pool 61 times; a full discovery day
  rewrites it 610 times. The write cost is quadratic in the pool's lifetime size.
- **Ten shards cannot share one pool file.** ADR-026 had to route every shard through its own
  artifact plus a serial consolidation job purely to avoid a write race on this one file.

## Decision
**Store the pool as one JSON file per symbol, under the directory `data/research_pool/`.**

`PartitionedExperimentStore(Path)` implements the existing `ExperimentStore` protocol:

- `add(exp)` reads and rewrites **only** `<dir>/<SYMBOL>.json`.
- `trials_for_symbol(sym)` reads **only** that symbol's file — the hot path in every hunt becomes a
  ~70 KB read instead of a 45 MB parse.
- `all()` globs the directory in sorted order and concatenates.

`JsonFileExperimentStore` is untouched and stays the store for **shard artifacts** — those are
transient, small, per-run files where a single array is the right shape.

A one-shot `scripts/migrate_research_pool.py` splits the existing monolith into partitions and then
removes it. This is a *migration*, not a deletion: every experiment is preserved byte-equivalently
in its partition, the monolith remains in git history, and the script refuses to remove the source
until it has verified that the partitions round-trip to the same experiment count and id set.

Symbols map to filenames through an explicit `_partition_name`: uppercased, with any character
outside `[A-Z0-9.^_-]` replaced by `_`. Real tickers (`BRK-B`, `^GSPC`, `BF.B`) are already safe;
the sanitizer exists so a malformed symbol can never escape the directory or the filesystem.

### Why per-symbol rather than per-date
Per-date partitioning bounds file size too, but per-symbol matches the *access pattern* and the
*write pattern*:

- The only hot read is `trials_for_symbol`, which is a symbol lookup. Per-date would still scan
  everything to answer it.
- ADR-026's shards are round-robin slices of the universe, so the ten writers touch **disjoint**
  symbol sets by construction. Partitioning by symbol makes the write race structurally impossible
  rather than avoided by orchestration.
- File size per symbol is self-limiting: one symbol accumulates ~14 KB per hunt, so a partition
  reaches 100 MB only after roughly 7,000 hunts of the same name. A date partition on a full
  discovery day is ~8.5 MB and would breach 100 MB inside a single month.

## Alternatives considered

- **Git LFS.** Rejected: it moves the bytes off the repository that Joe reads and reviews, adds a
  bandwidth quota to a project whose whole premise is that the pipeline is free, and does nothing
  about the O(n) write or the shard race.
- **Gzip the monolith.** Rejected: it buys one order of magnitude and loses the diffability that
  makes a committed pool auditable at all. It also leaves both the quadratic write and the race.
- **Prune harder.** Retention already exists (`prune_pool`, ADR-026: keep all graduates plus the 5
  most-recent non-graduates per symbol) and the 105 MB file was the *already-pruned* size — at 607
  symbols and 206 graduate experiments, that policy no longer bounds the pool below the wall.
  Tightening it further is lossy, and this ADR is not; partitioning fixes the wall without dropping
  a single row. Retention is not removed — it moves *into* the store so every writer applies it,
  rather than only the one script that remembered to call it. A stricter retention policy remains
  available later, on evidence, in its own ADR. Prefer the reversible option (charter §1).
- **Move the pool into TimescaleDB.** The right long-term answer (ADR-016 says so) and still the
  plan. It cannot happen now: the discovery workflows run on GitHub Actions with no database, and
  standing up a hosted one costs money the charter forbids.
- **Drop `strategy_names` and other redundant fields.** ~6% saving on a problem that needs 100×.
  Not worth a schema change.

## Consequences

- Every hunt gets faster: the per-experiment write goes from ~45 MB to ~70 KB.
- `git status` after a discovery day shows hundreds of changed small files instead of one huge one.
  Each is individually readable, which makes "what did the pipeline learn about AAPL" a one-file
  answer.
- Repository growth is unchanged in total bytes per day (~8.5 MB at full discovery). Partitioning
  fixes the hard 100 MB wall, not the growth rate; the growth rate is the next decision, and
  per-symbol partitioning is what makes a per-symbol retention policy implementable.
- Anything that referenced the pool by filename must now reference the directory: the two API
  routes, `hunt.py`, `run_hunt.py`, `paper.py`, `consolidate_pool.py`, `cron_hunt.sh`, and the
  `git add` steps in `hunt.yml` and `daily-discovery.yml`.

## Reversal
Run the inverse of the migration — concatenate `data/research_pool/*.json` in sorted order back into
`data/research_pool.json` — and point the callers back at `JsonFileExperimentStore`. The record is
identical either way; nothing about the schema, the gate, or the MinTRL denominator changes, which
is what makes this reversible at any time.
