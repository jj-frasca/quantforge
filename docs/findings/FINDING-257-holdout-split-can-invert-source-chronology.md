# FINDING-257: Positional holdout splitting can invert source chronology

- **Date:** 2026-10-16
- **Status:** Resolved — ADR-302
- **Area:** split_holdout, split_panel_holdout and direct single-name run_search

## Independent reproduction

Construct 1,000 UTC business-day bars starting 2020-01-01 with finite positive
geometric prices (NumPy default_rng seed 202610162301, log increments N(0,.01)).
Rotate the source with concat([frame.iloc[252:], frame.iloc[:252]]). Each resulting
split portion is unique and ascending internally, while the full source is not:

| Portion | First date | Last date | Bars |
|---|---|---|---|
| Search | 2020-12-18 | 2023-10-31 | 748 |
| Holdout | 2020-01-01 | 2020-12-17 | 252 |

Public run_search with actual catalog slug sma, n_per_param=2 and trial_budget=4
completes one family trial, three evaluated configurations and a failed verdict.
The holdout entirely predates the data that selected its finalist. The parent's
initial wrong slug sma_crossover refusal is not evidence of completed search;
the independent actual-slug run is. No false graduate is observed.

Both splitters also accept [Jan1,Jan2,Jan2,Jan3] with fraction .5/floors2. Each
half is individually unique and ordered but shares Jan2 across the cut. Thus both
whole-index uniqueness and order are required, rather than checking each half.

Review: `/tmp/qf-w42-s23-split-chronology-review.md`.
Receipt: `/tmp/qf-w42-s23-split-chronology-reproduction.json`.
All standalone searches/checks terminated; no source or generated record changed.

## Production mitigations and claim limits

ResearchDataset construction checks its whole source calendar and ADR-165 isolates
the retained frame. Normal run_universe_hunt uses that dataset, so the inversion
fixture does not bypass its production provider boundary. Single-name direct
DataFrame search is independently public, including synthetic calibration callers.
Their existing frozen sources are not shown malformed and must not be changed,
rerun or relabeled by this finding.

The panel splitter independently accepts the same inversion. Cross-sectional
holdout scoring later calls asset_returns on full prices, which rejects the whole
unordered calendar; no completed cross-sectional accepted verdict is claimed.
Single-name scoring instead validates only the sealed tail separately, leaving
its boundary relationship unchecked. Per-engine source-order validation is correct
on the portion each engine actually receives.

This establishes a direct original-source chronology defect, not a production
occurrence, real-market false graduate or changed measured calibration rate.

## Correction and verification

ADR-302 requires original unique ascending whole indexes at both splitters after
fraction validation and before length/slices/size work, preserving all valid
positional arithmetic and ordered generic/naive/aware compatibility. No sorting,
deduplication, timezone/cadence, threshold, estimator, accounting-v14 or generated
record change. Scalar floor-domain policy and frame ownership remain separate.

Actual preimplementation RED: 15 failures and 24 preserved controls in 3.29s,
`/tmp/qf-w42-s23-calendar-red.log`. After the two guards, all 167 focused tests
passed; independent review reran them successfully and approved all seven paths.
Hypothesis verifies strict split ordering, exact reconstruction and refusal of
nonchronological permutations. Ordered generic, MultiIndex, naive and aware
sources retain exact rows; valid short sources retain size refusal and fraction
validation stays first. Public run_search refuses before candidate allocation.

Parent and independent AST checks prove only the two guards and named docstrings
changed: signatures, fraction branch, complete size/arithmetic/slicing nodes and
all other executable source remain exact. Parent receipt:
`/tmp/qf-w42-s23-calendar-source-guard.json`. Generated-data status stayed clean.
Ruff lint/format and strict mypy (184 files) passed.

Foreground `make check-all PYTEST_WORKERS=8` completed green: 12,174 backend
tests, 97.40% backend coverage; 381 frontend tests, 97.66% frontend statements.
All lint, format and type checks passed. Log: `/tmp/qf-w42-s23-check302.log`.
No production source changed after the focused GREEN run.
