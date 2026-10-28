# ADR-391: Qualify diagnostics conditional on the realized adaptive grid

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Codex autonomous session10, ISO2026-W44
- **Addresses:** FINDING-332 reporting; nested adaptive evaluation remains open
- **Clarifies:** ADR-038/039/069/104/293

## Context

Longitudinal refinement chooses a grid using the entire search handle before
WF/PCV/CSCV resampling. F332's actual orchestration with controlled allocation
changes an early WF grid, selected config and score solely through later search
rows; a fixed-grid paired control matches exactly. Train-only argmax is causal
conditional on its supplied candidate set, not nested evaluation of that set's
adaptive construction. The sealed holdout remains separate and unchanged.

## Options Considered

1. **Qualify the existing diagnostic (chosen).**
   - Pro: directly supported, reversible, preserves all numbers and attribution.
   - Con: does not provide nested adaptive selection measurement.
2. **Rebuild allocation, coarse selection and refinement inside every fold.**
   - Pro: could evaluate the outer adaptive process using fold-specific training.
   - Con: different procedure, budget/cost/parameter identities and possible
     config spaces across folds; requires separate design, TDD and calibration.
3. **Drop refinement or its columns from diagnostics.**
   - Pro: removes this adaptive branch or simplifies the candidate set.
   - Con: changes search behavior or restores ADR-104's omitted-candidate defect.
     No evidence authorizes changing production or relabeling past measurements.

## Decision

Qualify the four leading docstrings in WalkForwardResult, walk_forward_evaluate,
_select_index and run_search. State conditional fixed-grid WF causality and the
full-search choice of refined candidates. Describe whole-search PBO as resampling
the realized matrix, not rerunning adaptive candidate construction. Update the
active architecture WF/PBO summaries, validation cold-memory PBO/WF/PCV contracts,
and backtesting cold-memory qualification; ship the self-contained written finding.
Leave accepted historical ADRs, numerical tables, UI and stored records unchanged.
This bounded correction is not an exhaustive audit of public descriptions.

No executable statement, estimator, schema field/constraint, serialized-result
shape, default, parameter grid, selector,
threshold, fingerprint or accounting identity changes. No new tests that mirror
wording: use the independent actual-engine/orchestration witness and existing
regressions, with AST and hash evidence for numerical preservation.
The WalkForwardResult class description in generated JSON Schema follows its
qualified docstring; this prose metadata changes without a field or constraint change.

## Consequences and verification

Readers can distinguish causal within-grid config selection from nested adaptive
search evaluation. Whole-search PBO must still include every evaluated refined
column. PCV remains deliberately noncausal fold selection. Continuation costs,
source dependence and source isolation retain their separate qualifications.
A matched full-procedure null/power can still measure the actual adaptive search;
no bias direction, affected graduate or invalid calibration rate is inferred.
All frozen cohorts and generated evidence remain intact; no new measurement runs.

Before source edits, freeze both module ASTs with only the four exact leading
docstrings removed; hash scientific gate/accounting/calibration/engine/grid/budget
modules and all existing tests, and capture search/gate fingerprints. Compare
these after edits, preserving every other string, import, node and constant.
Run existing WF/search regressions, independent final review and foreground
make check-all; publish individually with safe sync/push and exact CI checks.

Reversal restores these active descriptions without changing runtime behavior;
retain F332, reopening the reporting qualification. Nested adaptive validation
remains a separate open design, never an implicit implementation change here.
