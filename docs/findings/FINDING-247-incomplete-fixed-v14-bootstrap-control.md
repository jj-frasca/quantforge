# FINDING-247: The fixed v14 bootstrap:SPY control is incomplete

- **Status:** Incomplete execution; no Type-I inference
- **Date:** 2026-10-16
- **Scope:** Local operational evidence for the prospective empirical-SPY null control
- **Governing decisions:** ADR-036/037/044/291; frozen pre-search protocol

## Observation

Session 17 froze all 200 new bootstrap sources before any search. Session 19
found 52 durable Experiment checkpoints and 52 one-symbol calibration shards,
indices 0000 through 0051, plus 53 start markers, indices 0000 through 0052.
`V14BOOTSPY_0052` has a start marker without a durable Experiment completion;
147 sources were never started. No source error file, combined result, summary
or cohort invalidation is recorded. Those absences do not establish the cause
of missing completion, successful computation for that source or the original
execution's activity state.

The planned N=200 did not complete. No partial graduation, survival or component
rate, confidence interval or full-N Type-I inference is reported. Unresolved and
unstarted sources are not zeros, failures or omitted observations. The completed
prefix is not a replacement cohort. Current v14 bootstrap calibration remains
unmeasured; the separate completed F241 iid-normal and F243 Student-t5 controls
retain their own laws and identities without pooling.

## Frozen identity and containment

Executed revision `81e9429fcdaecb2e171fd38d16c0b77979572d0f`, accounting v14,
full-34 search `edb65cb596b9c2daabe2ba81bf5660a562dfc110beefcb16d493244679ad2459`,
gate `250856983fb58b7f0392157eef5c96960a26d0b2b3f81d063281bf6b18eeb493`.
Sources `V14BOOTSPY_0000..0199` use seeds 2026101506000+i and 7400 bars.
Search settings are default GateConfig, n_per_param=3, refine=True/span=.25,
observed selection, prior=0 and no store. The original `bootstrap_null` samples
empirical return rows iid with replacement, carrying each return's same source
bar geometry/volume and retaining the default first-source-close base.

The empirical input contains 8485 SPY bars and 8484 returns, acquired at
`379c6933ac0216af916ddd1293884f566d428c8a`, spanning 1993-01-29 through
2026-10-14. Its passed quality report retains 304 missing-bars warnings and one
survivorship information issue. These are potential-issue flags, without vendor
or market-truth certification. The measurement's later revision does not relabel
that acquisition provenance. Exact input copies and audit receipts are preserved.

Ordered source SHA256:
`2739de87202b7a258e029a883678af9a754c3f0bc9ded3635780174f97b78ccc`.
Archive SHA256:
`c4b9a9252591a10ee8e1e3765a35338b4aeb51637f50dab687283f8267a0b16e`.
Protocol SHA256:
`234630f5f557e50ba6c630441a729f0e1c517df6d3aba04f7baec17be11a6478`.
Frozen metadata SHA256:
`2f4a49abd13cf51d71985c55e26312854215088b15ce85a1a999338b2ba8b071`.

The fixed 5400-second budget permits fresh searches only in the first invocation;
later invocations permit completed-only replay. Preflight refuses a started
source missing its Experiment before archive reconstruction, budget claim or
search. The execution record's `protocol_sha256` field binds the frozen metadata
hash above; that metadata separately binds the actual protocol document hash.
No runner main/run/freeze invocation, retry, marker removal, clock renewal, redraw, new search
or repeated attempt to obtain completion/preferred outcomes is performed or
authorized here. Preserve the original input, sources, scripts, metadata,
execution identity, checkpoints and shards. Completed replay cannot supply the
missing completion. No threshold, generated data or production behavior changes.

## Verification and limits

The independent pre-search audit checked all 200 raw/canonical sources, exact
PCG64 row-draw laws, same-row geometry, first draw/default base, immutable input,
code/dependencies/settings and known seed registry. Receipt:
`/tmp/qf-w42-s17-v14-bootstrap/source-audit.json`
(`PASS_SOURCE_ONLY_PRESEARCH`), SHA256
`9617ea4d1e2559504192cb0360b8d1393280f3f6509ae8fde03d2cde9bd71e11`.

Session 19's separate parent operational audit verified all 53 start identities,
source/call/settings bindings, frozen archive/protocol hashes and execution
budget identity without reading checkpoint outcome contents:
`/tmp/qf-w42-s19-bootstrap-parent-operational-audit.json`, SHA256
`27c93d82153b54497baae4e1cea002a721d74b17d8a0eada8b18999879c03e54`.
The independent interruption audit verified all 200 original source laws and
raw/canonical/input bindings, all 53 marker identities, and all 52 Experiment
and shard checkpoint roundtrips. It checked selected/lifetime semantics and
individual gate predicates, including actual UTC calendar-span MinTRL. Original
sources, scripts and checkpoint bytes were unchanged afterward. It invoked no
search, generator or completed replay and computed no endpoint event counts,
rates or intervals. Receipt:
`/tmp/qf-w42-s19-bootstrap-incomplete-research-audit.json`
(`PASS_INCOMPLETE_ONLY`), SHA256
`04880454f842e5ce0e221e4818eee67a290308f86f73e4f5a80a5b7119a599f6`.
Independent research review approved this finding and its cold-memory notice.
Foreground `make check-all` passed 11,376 backend tests (97.34% coverage) and
363 frontend tests (97.63% statement coverage), with lint, formatting and strict
typing green. No executable behavior or tests changed.

Scratch root: `/tmp/qf-w42-s17-v14-bootstrap`; original bound runner:
`/tmp/qf-w42-s17-v14-bootstrap-bound.py`; adopted protocol:
`/tmp/qf-w42-s17-v14-bootstrap-protocol.md`. Scratch retention is not guaranteed.
This incomplete empirical-marginal control supplies no market-wide bound, power
measurement or ADR-102 probability-gate authorization. Historical generated
calibrations retain their recorded procedure identities.
