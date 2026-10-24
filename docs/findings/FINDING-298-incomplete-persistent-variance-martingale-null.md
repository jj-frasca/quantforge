# FINDING-298: The ADR-358 persistent-variance null is incomplete

- **Status:** Incomplete execution; no Type-I inference
- **Date:** 2026-10-24
- **Scope:** Local operational evidence for the prospectively fixed persistent-variance control
- **Governing decisions:** ADR-036/037/044/291/358

## Observation

Session 26 published ADR-358, verified its exact CI, froze all 200 original
sources and obtained the independent all-source pre-search receipt before
claiming one execution clock. Session 27 finds 97 START markers, indices
0000..0096, and 96 durable Experiment checkpoints and one-symbol calibration
shards, indices 0000..0095. `V14PVAR26_0096` has no durable completion; 103
sources have no START marker. No error, combined result, summary, final-audit
or invalidation artifact exists. These absences establish neither successful
computation for source 0096 nor an interruption cause or execution activity state.

The original 7,200-second soft admission clock began at
`2026-10-24T07:52:52.276330+00:00` and had elapsed at inspection. The recorded
tool session is unavailable; this is not proof about any operating-system process.
The planned N200 cohort is incomplete under its original one-use protocol.
No endpoint or component counts, partial rates, intervals or full-N Type-I
inference are reported. Unresolved and unstarted sources are not zeros,
failures or omitted observations. Persistent-variance calibration remains
unmeasured. Completed and incomplete historical cohorts retain separate laws
and identities; none supplies a replacement or pooled denominator.

## Frozen identity and containment

Executed revision `3c7e87d7c1a53a51e14ee5b31cc40079ffefb2ba`, accounting v14,
search `edb65cb596b9c2daabe2ba81bf5660a562dfc110beefcb16d493244679ad2459`,
gate `250856983fb58b7f0392157eef5c96960a26d0b2b3f81d063281bf6b18eeb493`.
Symbols `V14PVAR26_0000..0199`, seeds 2026102407000+i, 7,400 bars.

ADR-358 fixes integer initial price384, absorbing floor128, amplitude states1/4
and initial state1. Full independent sign and flip arrays precede every path;
flip probability1/50 acts after each price step. Symmetric capped increments
give ideal zero conditional mean simple returns; native ratio rounding has
the separately established 2^-54 paired-mean bound. The protocol specifies
causal OHLCV and a generic business-day UTC nanosecond calendar. This is a
law-specific stress, without market-realism or exact numerical-martingale claims.

The unchanged full34/defaultGate/budget200 procedure uses n_per_param3,
refine=True/span.25, observed selection, prior0 and no store;
search5,920/locked holdout1,480 bars. Execution and START `protocol_sha256`
fields bind frozen metadata, which separately binds the protocol document.

| Evidence | SHA256 |
|---|---|
| Ordered source digests | `c0a237a2c6aac75cee6dea91e2e39b075ab25567c9a32d5ce3a2b66e3acf01ea` |
| Source archive | `7abf0e54d6a700b84a31b77cc44b51c16a8b4c67a73729577399dbb1deb838bd` |
| Protocol document | `3232f9e0077455fa99c3877639029409ecafbd66bfc2640031ae0c1a691fa04e` |
| Frozen metadata | `dd49a2735c38c63f7b41a3163644d259f869ee32fd706ba2d29b4d7296098ec0` |
| Bound runner | `290924637bcf0fc2153f5839909146424c25d2113f3c9f50bdd2c39b54e85cb6` |
| Bound helper | `3e1b4df82692390922a6713ad5b287e24eb5e40c314fa8d648a831aa2b8ba1c1` |
| Bound independent auditor | `63a74d2d3421b72394185eb73fd86a7f879a9b74ff7a0a848025d1f7b8e9ae61` |

Preserve every original source, marker, checkpoint, shard, script and receipt.
No retry, fresh continuation, resume, redraw, source repair, marker removal,
budget renewal or replacement attempt is performed or authorized. Completed-only
replay cannot supply the missing completion. No generated data, threshold,
production behavior or accounting identity changes.

## Verification and limits

The original pre-search receipt in the cohort root is
`presearch-audit.json`, status `PASS_SOURCE_ONLY_PRESEARCH`, validated200/searches0,
SHA256 `1b82ff3ba7b7c29959e006025e907bea6654248d7ad0b7e34df6586e53047bd1`.
It binds the original archive, ordered sources, protocol, runner, revision and metadata.

Session 27's parent operational audit checked all 97 exact START/call identities,
96 completion attachments and authoritative Experiment/shard roundtrips,
receipt/clock bindings, and all 162 backend/app files against the executed
revision. All 294 cohort-file hashes were identical before and after. No RNG,
search, runner/helper import or endpoint aggregation was performed.
Receipt `/tmp/qf-w43-s27-persistent-operational.json`, status
`PASS_INCOMPLETE_ONLY`, SHA256
`984f54c133a56e0a3fcc0eb7a225333aa99cd755e5a29bbac200336e605cf207`.
Script `/tmp/qf-w43-s27-persistent-operational.py`, SHA256
`903b28a1095c7980feb3f2b6e1176712c9882ad1c70c05a14d0881e7b220459a`.

The independent research reviewer used the retained auditor's identity and
source functions to reconstruct all 200 exact seed/law/OHLCV/calendar/hash
paths and verify settings/environment/revision. A scratch AST-derived subset
of its final audit checked all 96 original completions: authoritative models,
observed finalist, refinement allocation, trial counts, fixed-config locked
holdout scores, MinTRL, six predicates and diagnostic/joint/shard bindings.
Endpoint accumulation, merge and complete-result certification were excluded.
All 297 snapshotted cohort and bound-script hashes matched before and after.
Receipt `/tmp/qf-w43-s27-incomplete-independent.json`, status
`PASS_INCOMPLETE_PRESERVATION_ONLY`, SHA256
`9639aa6c10bc2db1c06cfa238f818c22c1c45765b71b04165f50be1f46bf9ecf`.
Scratch audit-script SHA256:
`1f176f8a984d6194c33776abe4d24832711c6a517e9a7e50126c4fd8c8befc33`.
All 45 original per-checkpoint assertion ASTs remain identical and ordered;
extraction provenance receipt SHA256:
`0e61a3fbce982bcb143d65cd7c6c8ff89b0485b536a12e2cf452d764250ec0a9`.
This is checkpoint preservation, not a raw-candidate matrix rescan or a full
cohort scientific result. Neither audit invokes the runner or auditor CLI,
calibrate_gate, run_search, merge or a cohort writer. Deterministic source and
selected fixed-config score reconstruction checks equality without replacement.

Independent final research review approves this finding and cold-memory notice.
Fresh foreground `make check-all PYTEST_WORKERS=2` exits0: 14,537 backend tests
(97.41% coverage), 731 frontend tests (97.88% statement coverage), lint,
formatting and strict typing pass. Log `/tmp/qf-w43-s27-check298.log`.
No executable behavior or tests change.

Scratch root `/tmp/qf-w43-s26-v14-persistent`; runner is the adjacent `.py`.
Scratch retention is not guaranteed. No market-wide bound, arbitrary-variance
robustness, bootstrap calibration, AR power or ADR-102 probability-gate
authorization follows. Historical calibrations retain their executed identities.
