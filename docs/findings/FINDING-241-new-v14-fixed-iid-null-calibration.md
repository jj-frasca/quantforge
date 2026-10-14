# FINDING-241: New fixed v14 iid-normal null calibration

- **Status:** Measured; complete independently audited fixed cohort
- **Date:** 2026-10-14
- **Scope:** Local negative control of the unchanged full search/graduation pipeline
- **Governing decisions:** ADR-036/037/044, ADR-291

## Measurement

The new fixed cohort completed **200/200 searches, zero errors, zero graduates
and zero ADR-018 survivors**. The combined universe bar is 1.3432393159670402
at each 1480-bar holdout; the maximum trial-wide selection-adjusted Sharpe margin
is -0.5220103278468126. All selected-finalist OOS/control/probability fields are
measured for all200 symbols.

| Incumbent component | Passing finalists /200 |
|---|---:|
| Selection-adjusted margin | 0 |
| PBO | 181 |
| Parameter stability | 53 |
| MinTRL | 27 |
| Locked holdout | 126 |
| Beats buy-and-hold | 22 |
| Complete gate / ADR-018 survival | 0 / 0 |

Zero observed events is not a zero population error guarantee. Under this fixed
independently seeded iid law, the one-sided95% exact zero-event upper limit is
`1 - 0.05**(1/200) = 0.014867039231272057`, approximately **1.4867%**.
Graduation and survival are endpoints on the same200 sources, not400 independent
observations. The search/gate/reference/null parameters were never changed in
response to outcomes.

This new fixed cohort measures its executed v14 procedure only. It is not a rerun
or pooled denominator of any historical v10/v9 sources. No published generated
record was changed. Different seeds prevent attributing a difference versus
historical rates to code alone. Power, heavy-tail, bootstrap and real-market
coverage remain separate. This unique scratch cohort null-mode is not an
ADR-102 complete probability-gate comparison or threshold authorization.

## Frozen procedure

Exactly200 new iid_normal_null frames, IDs V14IID12_0000..0199,
seed2026101412000+i, 7400 bars, drift.0003, vol.012, start_price100.
All200 exact OHLCV/calendar/columns/dtype bytes and source digests were frozen
before any search. There is no exploitable serial structure by construction.
All34 catalog names in canonical order, n_per_param3, adaptive refinement enabled
with span.25, observed selection, default GateConfig/candidate budget200,
prior_trials0 and no ExperimentStore. Search5920/locked holdout1480 bars,
1480/252 years. Incumbent gate and strict ADR018 formula remain unchanged.

One-symbol unmodified calibrate_gate shards are durable exclusive checkpoints;
unmodified merge_calibrations reconstructs the combined N200 universe bar.
Shard survivor counts are never added. All complete results and the aggregate
are model-revalidated. Per-component counts use the selected finalist's canonical
joint verdict; diagnostic missingness keeps its own measured denominator.

Code66c1c5d829c9b2abba4482df4b0dae9143000ff7, accountingv14,
fullcatalog search edb65cb596b9c2daabe2ba81bf5660a562dfc110beefcb16d493244679ad2459,
gate250856983fb58b7f0392157eef5c96960a26d0b2b3f81d063281bf6b18eeb493.
Python3.12.13/NumPy2.5.3/pandas3.0.6/SciPy1.18.1/Pydantic2.14.0,
PCG64; complete versions and uv-lock digest are frozen in metadata.

## Pre-search refusal and reader amendment

The first runner refused in source-integrity preflight: pandas source indexes
used microseconds, but the archive decoder assumed nanoseconds. No search,
started marker or outcome checkpoint existed. Original runner, protocol,
metadata and source archive remained byte-for-byte intact. An independently
reviewed exclusive amendment binds their hashes to corrected reader-v2 before
first search. Explicit datetime64[us] view and UTC localization recover every
original source digest; no draw, source value, seed or calendar changed.
The next AR archive contract explicitly stores timestamp units.

Ordered source digest c1ae3fb3bddf157c2c5af5dba6262aeb739e78da4d2feaed78bab6d876e5635f.
Reader amendment8e649ffabff59e24cbc20ae7002efdd629deca772338bb140e677db5b46d175e.
The existing digest guard contained a scratch-reader failure rather than accepting
altered calendar evidence. Each completed record also binds that amendment.

## Evidence and limitations

Independent source audit verifies all200 direct PCG64 laws, hashes, finite
positive OHLCV, geometry, original calendar, grids, code and settings. Parent final audit independently counted all200 canonical joint verdicts,
checked every checkpoint against its original source/protocol/amendment/start
identity, model-revalidated each shard and the aggregate, reproduced the official
merged payload exactly, and independently calculated the strict N200 universe
bar, component counts and zero-event bound. The final research-expert audit approved all200 source/checkpoint/start/amendment
identities, exact strict-JSON roundtrips, complete revalidated merge bytes,
manual bar/joint/component/missingness counts and stable zero-event bound.
The persisted trial-wide maximum agrees with the per-shard API summaries;
full raw trial Experiments were not retained, so no independent raw-trial rescan
is claimed. The full foreground `make check-all` delivery gate passed: 11,311 backend and
363 frontend tests; coverage97.38%/97.63%; Ruff, formatting, mypy, ESLint and
TypeScript checks green. Receipt: /tmp/qf-w42-s12-check241.log, closed exit0. Sources/results/protocol/runners and audits live under
/tmp/qf-w42-s12-v14-iid and /tmp/qf-w42-s12-v14-iid*. Scratch retention is not
guaranteed; scientific reproduction requires the stated exact law, seeds, code,
dependencies and protocol rather than invented replacement records.

Complete measurement elapsed2290.075839 seconds. Result SHA256
`d577864de091b733cb35476f0793dffdf0000e16cdbc5a4f5e7c3d4061a9d350`;
frozen metadata SHA256
`357ef247567c70acc1978f40114f59c6d15aa0823d59dc5accabf5eeb4d0e571`.

Final independent receipt: `/tmp/qf-w42-s12-v14-iid-final-research-audit.json`.
