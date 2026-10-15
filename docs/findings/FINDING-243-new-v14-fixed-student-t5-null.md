# FINDING-243: New fixed v14 Student-t5 null stress

- **Status:** Complete fixed cohort; independently audited and verified
- **Date:** 2026-10-14
- **Scope:** Local fixed-cohort heavy-tail stress of the unchanged search and gate
- **Governing decisions:** ADR-036/037/044/291

## Measurement

All **200/200 searches completed, with zero errors, zero graduates and zero
ADR-018 survivors**. The official combined-N200 bar is 1.3432393159670402
at each 1480-bar holdout. All five selected diagnostic/probability fields are
measured for all 200 symbols. The maximum over the retained **7,000 compact Trial
records** is -0.318635506435056, matching the production calibration summary;
this is not a rescan of raw concrete-config return matrices.

| Incumbent component | Passing finalists / 200 |
|---|---:|
| Selection-adjusted margin | 0 |
| PBO | 179 |
| Parameter stability | 53 |
| MinTRL | 16 |
| Locked holdout | 119 |
| Beats buy-and-hold | 28 |
| Complete gate / ADR-018 survival | 0 / 0 |

The fixed zero-event upper limit is **0.014867039231272057**, approximately
**1.4867%**, separately for each endpoint under the stated stress model.

The prospective analysis uses marginal one-sided exact 95% upper limits at every
count k, Beta.ppf(.95,k+1,200-k) for k<200 and 1 at k = 200; at zero the stable
-expm1(log(.05)/200) expression applies. These are not zero-error guarantees or
simultaneous-coverage claims. Graduation and ADR-018 survival are correlated
endpoints on the same 200 sources. Scope is the stated
completed valid-source stress model, not real markets or arbitrary nulls.

## Frozen procedure and identity

All 200 NEW sources V14T5_0000..0199, independent seeds 2026101418000+i,
7,400 bars, start 100, simple returns .0003+.012*sqrt(3/5)*standard_t(5).
Same RNG continues for original null OHLCV geometry/volume draws. All sources
were exclusively archived before any search; any invalid/nonpositive/nonfinite
source would invalidate the entire cohort without redraw, clipping or replacement.
The ideal source law has variance .012**2 and raw kurtosis9, finite fourth and
infinite eighth moments. Conventional sample-kurtosis precision is not certified.

All 34 canonical families, default GateConfig/candidate budget 200, n_per_param = 3,
refine = True/span = 0.25, observed selection, prior = 0/no store, train 5,920/holdout 1,480.
Official one-symbol calibrate_gate shards and official merge_calibrations at
combined N = 200; never add shard survivor counts. Record-only observer returns each
same unmodified Experiment after its durable exclusive validated checkpoint.

Executed code a8054a5d991eb224a0de820c1abbdabe5a4cf37a, accounting v14,
search edb65cb596b9c2daabe2ba81bf5660a562dfc110beefcb16d493244679ad2459,
gate 250856983fb58b7f0392157eef5c96960a26d0b2b3f81d063281bf6b18eeb493.
Python 3.12.13/NumPy 2.5.3/pandas 3.0.6/SciPy 1.18.1/Pydantic 2.14.0/PCG64;
full dependencies, code/import provenance, catalog/grids and settings are frozen.

Ordered source SHA256: 7b88550dd71771cdda9a3bada697754f61cc14fc51edc2a4cc825496b5770b70.
Archive SHA256: 557961a4eecac232414ae125aa6cd289c53403896727d104ed7dbc75fbdbdae8.
Metadata SHA256: 997aea23798c23267aae290505075ff2f60a34ed9a65ea063b213588015e446a.
Protocol SHA256: 89287b447c1e9554e8126d77e467caa7128249fcd1d6b44f616157c817d0b933.

## Execution and verification

Before source generation, independent review caught budget renewal on restart
in the scratch draft. Six failing scratch checks preceded the correction.
The frozen runner now records one exclusive execution identity and fixed 5,400s
budget; only its first invocation may start fresh sources. Later invocations
permit completed-only replay. Unresolved starts/errors refuse, never becoming
zeros or omitted draws. No source law, threshold or analysis changed.

Pre-search independent source audit matched all 200 exact PCG64 source arrays,
continued geometry/volumes, calendar units, digests, code/dependencies and settings.
Receipt /tmp/qf-w42-s14-t5-source-research-audit.json.
Parent complete-only audit independently verified all 200 checkpoint/start/source
bindings, component conjunctions, strict universe survival, selected-field
missingness, all 7,000 retained compact Trial records and both exact binomial
bounds. Source/archive/protocol/runner identities remained unchanged. Receipt:
`/tmp/qf-w42-s14-t5-parent-audit.json`, freshly reproduced in session 15 at
`/tmp/qf-w42-s15-t5-parent-audit.json`. The prepared independent final checker
initially stopped on its own incorrect MinTRL span assumption (5,920/252);
production uses elapsed calendar days/365.25. The original checker is preserved,
and a separate corrected checker passed every original check with the actual
calendar-span predicate. It independently matched all source-law/hash/code and
dependency identities, 200 start/checkpoint roundtrips, selected identities and
lifetime counts, all six component predicates, exact official shard/merge bytes,
and both confidence bounds, with zero new searches. Final receipt:
`/tmp/qf-w42-s15-t5-final-research-audit.json`.

Retained full Experiments contain compact Trial summaries,
not every raw concrete-config return matrix; no raw-config rescan is claimed.
Complete measurement elapsed 2311.4629443008453 seconds. Result SHA256
`e5e10c734e6307239d9c3e61ab64c7acdb68c7c9c60f650f9bfdc5682fc19397`.
Fresh session-15 foreground `make check-all PYTEST_WORKERS=8` passed:
11,311 backend tests, 97.38% coverage; 363 frontend tests, 97.63% statement
coverage; Ruff lint/format, strict mypy, ESLint and TypeScript checks passed.
Terminal log: `/tmp/qf-w42-s15-check243.log`. Required independent final
review approved all three documentation paths. No production code changed.

Scratch root /tmp/qf-w42-s12-v14-t5; runner /tmp/qf-w42-s12-v14-t5.py.
Scratch retention is not guaranteed. This is a new cohort, not a rerun, redraw
or pooled denominator of historical F163 v10 or F241 iid sources. Differences in seeds/laws and, for F163, accounting version preclude a code-only
improvement claim; F241 and this cohort both use v14 accounting. Power/bootstrap/market
coverage remain separate; F242's AR run remains incomplete. No generated project
data, dashboard artifact, threshold, selector, catalog, gate or reference changes.
This custom stress mode is not a complete ADR-102 candidate-gate comparison.
