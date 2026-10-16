# FINDING-253: Persisted counters can understate their own evaluations

- **Date:** 2026-10-16
- **Status:** Resolved — ADR-299
- **Area:** Trial, Experiment, CrossSectionalExperiment and memory-store inputs

## Reproduction and consequence

At 0c7d4731, construct a valid Trial with name "manual", empty parameters,
observed Sharpe1, margin.5, PBO.1, stability.8 and n_evaluated_configs=4. Both a
single-name Experiment and a CrossSectionalExperiment accept that one trial and
lifetime_trials=1. Their JSON roundtrips retain lifetime1/evaluated4. Their memory
stores return prior1. Parent and independent research-expert probes reproduced
both paths without searches or generated-file writes.

A subsequent four-configuration run would compute lifetime5 from that prior,
versus at least8 consistent with the recorded four earlier evaluations. ADR-295
accepts positive integral prior1, so input validation alone cannot recover lost
accounting. Another larger stored counter can mask this particular row.

Both root counters also accept original True, 1.0 and Fraction(1,1), and currently
accept negative integers. Trial counters coerce True, 4.0 and Fraction(4,1).
Genuinely fractional counts reject; this finding makes no truncation claim.
Unchecked model copies additionally bypass memory-store append validation.

These are synthetic claim-boundary defects. They do not establish historical
production undercount, a false graduate or a revised calibration rate.

## Fresh compatibility evidence

Audit at full revision 0c7d47311a3485dd7eab4d6ab3694d84fd1080f5:

- Single-name: 607 files, 3,294 experiments, 113,476 compact trial summaries;
  113,319 explicit integral counts and 157 absent legacy fields retaining default1.
- Cross-sectional: one file, 24 experiments and 300 explicit integral trial counts.
- All 3,318 root counters are nonnegative original integers, all present trial
  counts positive original integers, and every lifetime covers its local sum.
- All actual current models reload; zero anomalies or deficits. All 608 source
  JSON files and model-source hashes unchanged before/after; no data writes.

Receipt: `/tmp/qf-w42-s21-persisted-count-compat-audit.json`, SHA256
355fb379852ecd7cfca8cd29b85ddb3503c7e4215715d445c0bdfacd25deefd8.
Ordered source aggregate:
c65efde0333c175c2ba2c589dd75d14e3a9dc309ad9fdf3676383b430b8b1e07.
No missing historical count is reconstructed; compatibility does not certify
unrecorded trials or monotonic chronology across old reset-era observations.

## Governed correction

ADR-299 validates original count domains before coercion and enforces the local
lifetime lower bound after existing lineage validation. Preserve default1,
empty-trial zero, larger priors, Python-int arithmetic, JSON shapes and all
aggregation/retention rules. Memory stores reconstruct before append; JSON stores
already reconstruct through the same model boundary before filesystem changes.
Memory storage retains equal validated snapshots rather than caller identity.
No generated records, threshold, formula, fingerprint or frozen cohort changes.

## Verification

Final pre-implementation run observed 60 genuine failures and 22 preserved
controls in 2.85 seconds (`/tmp/qf-w42-s21-persisted-final-red.log`). Initial
receipt is retained; the final test draft additionally removes legacy fields
from reload payloads to test actual omission before any production change.
After correction all 260 affected tests passed, including 82 new cases and the
Hypothesis accounting-bound property. Independent review reran all 260 and
approved all nine paths. No existing tests were edited or removed.

The post-change actual-model audit again loaded all 3,318 experiments, with zero
counter anomalies or deficits and the exact same 608 source JSON hashes/counts.
Its ordered source aggregate matches the pre-change identity above. Receipt:
`/tmp/qf-w42-s21-persisted-count-postchange-audit.json`, SHA256
`a02a80d72b65db7aea153139b12dbdff11895d8e0f18799ce0f829e2835ea1b9`.
The pre-change receipt remains byte-identical. No generated file was authored.

Parent source audit confirms only five named counter validators, two memory-add
bodies and imports changed executable source; model fields/defaults, searches,
gates, aggregation, retention and JSON I/O syntax remain exact
(`/tmp/qf-w42-s21-source299.json`).

Foreground `make check-all PYTEST_WORKERS=8` completed successfully: 11,979 backend
tests, 97.39% coverage; 381 frontend tests, 97.66% statement coverage. All lint,
format and type checks passed. Receipt: `/tmp/qf-w42-s21-check299.log`.
Exact master CI is checked after individual push.
