# ADR-303: Bind discovery to one fresh shared revision per attempt

- **Status:** Accepted
- **Date:** 2026-10-16
- **Deciders:** Codex autonomous session 23, ISO 2026-W42
- **Resolves:** FINDING-258
- **Extends:** ADR-026/030/032/062/090/151/154

## Context

Daily discovery serializes workflow runs but checks out their triggering ref/SHA.
A run queued before its predecessor publishes can start afterward with the old
committed-pool prior. Under the existing repeated-evaluation accounting policy,
event R0/prior100 plus four candidates reports104, even after predecessor R1 has
published104 and a fresh start should report108. Rebase after search cannot reprice
already-computed statistics. This is a concrete configuration/source route and
local Git model, not an observed production queue incident or false graduate.

Default checkout behavior is documented in the
[checkout v5 primary source](https://github.com/actions/checkout/blob/v5/README.md).
ADR-151 resolved the same queued-start freshness distinction for paper accrual;
its recorded incident does not establish a discovery incident. ADR-062 explicitly
chooses repeated candidate evaluations as a conservative breadth upper bound,
not four necessarily distinct hypotheses in this example.

## Options considered

1. Freeze current master once after the workflow concurrency wait; share its SHA
   across all shards and consolidation. Selected for coherent code and pool prior.
2. Set ref:master in each shard independently: smaller diff, but unrelated commits
   arriving between runner starts could mix executed revisions within one attempt.
3. Refresh only at consolidation: too late to repair the prior used during search.
4. Cancel pending runs or redesign queue ordering: changes requested coverage and
   does not establish scientific revision identity. Outside this decision.

## Decision

Inside the existing non-cancelling daily-discovery concurrency group, a bounded
preparation job explicitly checks out master and captures actual git rev-parse HEAD.
Validate a full lowercase 40-hex SHA and canonical positive current run-attempt
string before emitting either. All matrix and consolidation checkouts consume that
same immutable output, binding science code, committed prior and universe file.
No job independently resolves moving master afterward for scientific computation.

Both consumers preflight the full SHA and positive prepared attempt before checkout,
requiring exact string equality with the current attempt. A failed-only rerun that
reuses earlier successful preparation refuses with a rerun-all-jobs instruction.
A full rerun prepares a fresh snapshot. Attempt-qualify shard upload names and the
consolidation download pattern so a fresh attempt cannot consume earlier shards.
Current-run artifact lookup supplies run identity; no cross-attempt fallback exists.

Discover depends on preparation. Consolidation depends on both and retains always
execution only when preparation succeeded; its own preflight still refuses stale
outputs. Preserve existing partial-shard handling within the current attempt,
retry/yield rules, schedule, ten-shard assignment, manual universe input, catalog,
thresholds, search count recipe, retention and sole-writer boundary. No workflow is
dispatched as part of this change and no runner type or billable service is added.

SHA checkout leaves consolidation detached. Before its generated-data commit,
create a runner-local discovery-publication branch and push explicitly with
origin HEAD:master after existing pull/rebase retries. Do not force or publish that
local branch name. Existing generated-content conflicts still fail; no automatic
JSON conflict resolution or new publication recovery path is introduced.

Manual dispatch from another ref now deliberately selects science code and universe
files from fresh master. The triggering workflow definition/DAG remains event-bound;
it is distinct from the actual git-derived revision already recorded in experiments.
Live vendor retrieval times are not synchronized. No new persisted field, statistic,
gate predicate, threshold, accounting-v14 identity, calibration or generated record
is authored by this source change. A count not recorded historically is not inferred.

## Verification and reversal

Observe workflow-contract RED before YAML changes. Execute extracted preparation
and consumer scripts only with local fixtures; reject missing/malformed SHA/attempt
and stale output before checkout. A disposable local bare Git model must show the
old event checkout's104 versus fresh shared108, identical shard snapshots despite
an unrelated master advance, and detached-to-local-branch rebase/publication retaining
both108 and unrelated code. Cover failed preparation admission, attempt-isolated
artifacts, preserved current-attempt partial shards and universe input. Independent
review and foreground make check-all precede individual push and exact CI. No vendor,
workflow dispatch, credential, cloud resource provisioning or strategy search is used.

Restore event-time checkouts, run-only artifact names and prior publication commands
to reverse, reopening FINDING-258. No evidence migration is necessary.
