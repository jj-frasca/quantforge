# FINDING-245: The separate prospective v14 AR attempt is incomplete

- **Status:** Incomplete execution; no power inference
- **Date:** 2026-10-15
- **Scope:** Local operational evidence for the separately prospective strong AR control
- **Governing decisions:** ADR-041/044/291; frozen pre-search protocol

## Observation

The separate prospective attempt authorized in session 15 froze all 400 sources
before search: N=200 each at phi -0.30 and +0.30, paired by shared innovations.
Session 17 found 69 durable Experiment checkpoints, indices 0000 through 0068,
and 70 started markers, indices 0000 through 0069. The started source
`V14AR14_NEG_0069` has no durable completion. There are no recorded source
error files, arm results or arm summaries. Those absences do not identify the
cause of missing completion, establish successful computation for that source,
or establish the original execution's activity state.

Neither arm completed its planned N=200. This finding reports operational
accounting only, without partial detection, survival, component-pass rates,
confidence intervals or full-N power inference. Unresolved and unstarted sources
are not failures, zeros or omitted observations. The completed prefix is not a
replacement cohort. The positive arm remains unmeasured.

## Frozen identity and containment

Executed revision `379c6933ac0216af916ddd1293884f566d428c8a`, accounting v14,
full 34 search `edb65cb596b9c2daabe2ba81bf5660a562dfc110beefcb16d493244679ad2459`,
gate `250856983fb58b7f0392157eef5c96960a26d0b2b3f81d063281bf6b18eeb493`.
Every source has 7400 bars, drift .0003, innovation vol .012 and start price 100;
pair i uses seed 2026101421000+i. Search uses default GateConfig, n_per_param=3,
refine=True/span=.25, observed selection, prior=0 and no store. The specified
legacy lagged-sign reference retains FINDING-155's omitted-drift qualification.

Ordered source SHA256:
`45abc9349fc7e8138e55d315bb3059c81f0564d428aa0ac08c7262235bc5d35f`.
Archive SHA256:
`e5c6868b1359fd829ebb58c726f2e1d9297286320d15cbc8f726504bbf1f1b18`.
Protocol SHA256:
`84794ea4acd11ac59c42c426efaf34c6c6e3b4766f0208464a0d922ca95495cf`.
Frozen metadata SHA256:
`02a2b54376acf42a029c712bad967311b1757a8d0df45eb417c867c844c2a1ee`.

This was exactly one separate prospective attempt after F242, with new disjoint
seeds fixed without interpreting F242's prefix outcomes. It does not complete,
replace or pool that older cohort. Its protocol explicitly states: "If this
attempt is incomplete, retain it as incomplete; do not repeat attempts until a
complete or preferred result appears."

The fixed 7200-second operational budget and exclusive execution identity permit
fresh searches only on the first invocation; later invocations can replay
completed checkpoints only. Preflight also refuses any started source lacking
its Experiment. No source retry, marker removal, budget renewal, source redraw,
new search or further replacement attempt is performed or authorized here.
The original protocol, runner, sources, metadata, execution identity and
checkpoints remain preserved. Replaying completed evidence cannot supply the
missing completion. A future review must not reopen this attempt or silently
launch another cohort to obtain a completed result.

## Verification and limits

The independent pre-search source audit verified all 400 PCG64 laws, raw and
canonical observations, paired innovations, calendars, geometry, source hashes,
code/dependencies and settings before any search. Receipt:
`/tmp/qf-w42-s14-v14-ar-source-research-audit.json`
(`PASS_SOURCE_ONLY_PRESEARCH`).

Session 17's independent interruption audit validated all 400 original raw and
canonical sources against their independent PCG64 laws and paired innovations,
all 70 start-marker identities, and all 69 completed Experiments with exact
validated evidence roundtrips. It checked frozen code/dependencies, full catalog
settings and execution identity. All original file hashes were unchanged before
and after audit. It performed no search, source draw or prefix outcome-rate
calculation. The source count partitions as 69 completed, one unresolved start
and 330 never started; these are operational counts, not statistical outcomes.

Receipt: `/tmp/qf-w42-s17-ar-interruption-research-audit.json`
(`PASS_INCOMPLETE_ONLY`), SHA256
`19dc0cbeb1fdc01ae261908992009026c581630bd9a2cd93b75eaadab1b7b37f`.
The separate parent operational audit verified all start identities, frozen
hashes and execution budget without reading outcome content:
`/tmp/qf-w42-s17-ar-parent-operational-audit.json`.
Source review confirms the unresolved-start preflight refuses before archive
reconstruction, budget claim or search; the runner was not invoked.
Independent research review approved this finding and its active cold-memory
notice. Full foreground `make check-all` passed 11,376 backend tests
(97.34% coverage) and 363 frontend tests (97.63% statement coverage), with
lint, formatting and strict typing green. No runtime behavior changed.

Scratch root: `/tmp/qf-w42-s14-v14-ar`; original runner:
`/tmp/qf-w42-s14-v14-ar.py`. Local scratch retention is not guaranteed.
F242 remains separately incomplete; historical v10 power, F241 v14 iid and
F243 v14 Student-t5 retain their own identities. No generated data, threshold,
source law, reference calculation or production behavior changes here.
