# FINDING-197: OOS evaluators discard masked split row identity

- **Status:** Corrected
- **Date:** 2026-10-11
- **Severity:** Medium — unidentified observations affect selection and OOS evidence
- **Scope:** walk_forward_evaluate / purged_cv_evaluate caller split indexes
- **Decision:** ADR-248
- **Prior art:** ADR-199/FINDING-136 and ADR-200/FINDING-137, return masks

## Evidence

For six return rows [[.01,0],[-.1,.2],[.03,-.01],[.04,-.02],[.02,-.03],[.01,-.04]],
train indexes [0,1] masked [False,True] and test indexes [3,4] are accepted by both
OOS evaluators (purged embargo 1). Materialization discards the missing identity,
selects configuration 1 and reports n_train=2 / n_test=2, OOS Sharpe about -56.125.
The known-only train [0] selects configuration 0; this demonstrates the hidden
identity's effect, not a proposal to drop it. Entirely masked training and masked
test identities are likewise scored and counted from their storage indexes.
Independent synthetic reproduction confirmed these paths.

ADR-199/200 protect return masks, whereas the ADR-197/198 row-geometry boundaries
lose split-index masks. No canonical producer is known to emit masked splits;
no actual production leakage, revised calibration rate or false graduate is
inferred. No real search, cohort or generated artifact was rerun.

## Correction and verification

ADR-248 retains original index sources and refuses missing identities before
scoring or empty-fold dropping, while preserving complete-mask and geometry
semantics. The purged empty-fold conditional retains all kept-fold geometry
refusals before mask validation, then drops only complete empty folds.

Before code, 15 regressions failed and 13 preservation cases passed. All 110
affected tests pass after the guards, including train/test partial/all masks,
before-score spies, missing identity in a dropped fold, caller nonmutation,
complete masks, existing geometry precedence and Hypothesis mask combinations.
Independent review approved 160 exact published-baseline complete result JSON
probes across both generated evaluators, ten synthetic seeds, signed/unsigned/list
rows, all-false masks and present/absent benchmarks. Two additional probes retain
empty-fold dropping even with dormant noncontiguous tests. Masks/storage and
the calibration version remain unchanged.

The full foreground backend/frontend delivery gate is required before shipping.
No imputation, filtering, estimator, threshold or identity-version change.
