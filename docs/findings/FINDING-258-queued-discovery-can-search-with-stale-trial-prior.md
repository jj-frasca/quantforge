# FINDING-258: Queued discovery can search with an event-time trial prior

- **Date:** 2026-10-16
- **Status:** Resolved — ADR-303
- **Area:** daily-discovery workflow checkout, prior and attempt identity

## Source route and deterministic example

The workflow has a non-cancelling concurrency group but default event-time
checkouts. shard_hunt reads its checkout's committed partitioned pool through
PriorAwareExperimentStore and records actual git revision. Consolidation does not
recompute the gate at a newer prior; its later rebase cannot change that calculation.

A concrete possible sequence under ADR-062's existing accounting policy:

1. A starts from R0/prior100; B is requested then, binding its event to R0.
2. A evaluates four configurations and publishes R1/prior104.
3. B starts after A finishes, but default checkout still restores R0/prior100.
4. B evaluates four configurations and reports104, whereas fresh R1 implies108.

This is four omitted repeated evaluations under the stated conservative policy,
not proof of four distinct hypotheses. The represented maximum need not fall:
both searches can report104, so retention's maximum witness cannot repair the
omitted increment or reprice B's statistics. Publication might later fail on a
separate generated-content conflict; this finding does not assert stale output
necessarily reached master.

[checkout v5](https://github.com/actions/checkout/blob/v5/README.md) documents the
default triggering ref/SHA.
[workflow dispatch documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch)
and [concurrency documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
support the distinction between event binding and serialized execution. ADR-151's
actual paper incident is a different workflow, not evidence of a discovery incident.

Independent review and local arithmetic model:
`/tmp/qf-w42-s23-discovery-queued-prior-review.md` and
`/tmp/qf-w42-s23-discovery-queued-prior-model.json`.
A separate disposable shallow Git model verified shared fresh revision checkout,
runner-local publication branch, rebase over unrelated code and explicit HEAD:master:
`/tmp/qf-w42-s23-discovery-frozen-revision-model.json`.
No actual workflow, vendor, strategy search or broker was invoked.

## Correction and limits

ADR-303 freezes current master once per attempt after the existing concurrency
wait; shards and consolidation consume the same validated immutable SHA. Consumer
preflight rejects stale prepared attempts before checkout, and artifact names and
downloads isolate the current attempt. Failed-only reruns with reused preparation
must rerun all jobs. Consolidation still tolerates current-attempt partial shards
when preparation succeeded; no success threshold or yield rule is relaxed.

The detached consolidation checkout uses a runner-local publication branch and
explicit HEAD:master, retaining existing retry/conflict failure behavior. Manual
other-ref dispatch deliberately uses fresh master science code/universe files;
the event-selected workflow DAG remains distinct. Actual experiment git lineage
stays authoritative, not the run's event head_sha.

No observed production queue incident, false graduate, calibration-rate change or
historical count reconstruction is claimed. No search formula, threshold, v14,
provider schedule, scientific schema or generated record is changed. Live source
retrieval is not synchronized and concurrency is not a lossless FIFO queue.

## Verification

Actual preimplementation workflow/script RED observed 45 failing tests in 0.89s,
`/tmp/qf-w42-s23-discovery-red.log`. Missing required safe steps refused extraction
before any old hunt script could execute. After the YAML correction, all 68
focused workflow tests passed, including 45 new contracts/executable-script cases.
Ruff lint/format, strict test-file mypy and local actionlint passed.

The executable fixture used only disposable local bare Git repositories and plain
COUNTER.txt records: stale event prior100+4=104, freshly prepared104+4=108;
two depth-one shard checkouts retained the same prepared SHA despite unrelated
master code advancing. The actual publication script created only a local branch,
rebased the unrelated code and published prior108 via HEAD:master to the local
bare remote. No discovery-publication branch was pushed. Malformed/missing SHA,
noncanonical or stale attempt values refuse; large matching attempt strings avoid
integer coercion. Current-attempt partial-shard admission and manual universe input
remain covered.

Parent source comparison proves the old hunt, consolidation and summary script
bodies unchanged, with publication changes confined to local branch creation and
explicit destination. Global triggers, concurrency, permissions and environment
are exact; consumer guards are identical. Receipt:
`/tmp/qf-w42-s23-discovery-source-guard.json`. Independent final six-path scientific
review approved. Generated-data status stayed clean.

Foreground `make check-all PYTEST_WORKERS=8` completed green: 12,219 backend
tests, 97.40% backend coverage; 381 frontend tests, 97.66% frontend statements.
All lint, format and type checks passed. Log: `/tmp/qf-w42-s23-check303.log`.
Workflow source stayed unchanged after the focused GREEN run.
No discovery dispatch, vendor data, credentials or remote service execution was
used for these local tests.
