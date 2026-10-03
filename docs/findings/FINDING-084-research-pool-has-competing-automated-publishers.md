# FINDING-084: The research pool has competing automated publishers

- **Severity:** High — completed research can fail publication or leave a divergent local commit
- **Status:** Resolved by ADR-154
- **Date:** 2026-10-02
- **Affects:** ADR-026, ADR-030, ADR-032, `daily-discovery.yml`, `hunt.yml`, and `cron_hunt.sh`

## Finding

Three automated paths publish `data/research_pool`: daily discovery, the scheduled weekly hunt, and
the local hunt fallback. The cloud workflows use unrelated concurrency groups and begin from their
run-creation revisions. Both can spend hours changing the same per-symbol JSON partitions, commit
those stale-base results, and only then pull with rebase. If another publisher changed an overlapping
partition, Git cannot semantically merge the generated JSON. Retrying the same conflicted rebase
does not recover the completed research. The local fallback is less safe: it performs a bare push,
so rejection leaves its generated-data commit divergent locally.

Partitioning makes parallel daily shards safe because their symbol sets are disjoint inside one run.
It does not make two whole-universe publishers disjoint. A shared GitHub concurrency group would
also be lossy because only one pending run is retained and a newer request can replace it.

The extra weekly publisher adds no scheduled coverage. `data/universes/discovery.txt` strictly
contains every symbol in `data/universes/sp500.txt`, and daily discovery already searches that
superset every weekday with the same catalog and gate.

## Required correction

Make daily discovery the sole automated publisher of the research pool. Retire the redundant
scheduled-hunt workflow and its local committing fallback. Keep daily discovery's manual universe
input as the recovery and custom-universe entry point, and keep the underlying hunt driver available
for deliberate local research without an automated commit/push wrapper.

Add a repository contract proving exactly one workflow stages the pool and that no local fallback
script commits it. Do not rewrite existing pool evidence, weaken any gate, or dispatch a hunt while
implementing the correction.
