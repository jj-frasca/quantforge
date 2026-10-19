# ADR-321: Measure cross-sectional family walk-forward diagnostics

- **Status:** Accepted
- **Date:** 2026-10-19
- **Deciders:** Codex autonomous session 1, ISO 2026-W43
- **Extends:** ADR-024/038/068/104/142/145/150/291/293
- **Addresses in part:** FINDING-265

## Context

Cross-sectional search records walk-forward and purged split counts without
evaluating either. Its existing allocated family return matrices support the
same train-selected continuation-window statistic as longitudinal validation.
An independent review supports a backend measurement slice with durable paired
evidence. Purged evaluation needs separate factor dependency and embargo design;
hidden default windows and combined lookbacks make a maximum-grid-integer proxy
insufficient here.

## Decision

Evaluate each complete allocated family matrix with the unchanged
walk_forward_splits and walk_forward_evaluate. Build one search-only benchmark
from asset_returns(in_sample).mean(axis=1), including its existing initial zero,
and supply its native array to every evaluator. Use exactly the generated test
rows and equal mean of window Sharpes. The benchmark represents equal-weight
universe returns, with no additional turnover-cost model.

Attach each full result and actual split count to its ephemeral ValidationReport.
Persist its mean in inherited CrossSectionalTrial.walk_forward_oos_sharpe.
Persist four nullable experiment fields: walk_forward_method with literal
family-walk-forward-equal-weight-continuation-v1, walk_forward_hold_sharpe,
walk_forward_n_bars, and walk_forward_n_splits. The latter two record the actual
search row count and evaluated split count. Producer checks must establish the
same paired benchmark and geometry for every family before compact publication.

When method is present, require nonempty trials, every family mean, a finite
common benchmark and complete geometry. Counts require original nonboolean
Integral evidence normalized to Python int; splits >=1 and bars >=splits+1.
Unknown methods refuse. Method absent retains legacy null and unpaired trial
scalars; new pairing/geometry fields must also be absent. Existing claim-graph
reconstruction and store validation enforce the measured branch, including
unchecked model copies. Compact scalar persistence is not a per-split audit trail
or proof of source provenance, and method/geometry alone do not make two panels
or parameter populations comparable.

Evaluator errors propagate. Numerically unmeasurable training, test or benchmark
blocks can now refuse an otherwise successful search. Never fabricate a score,
mask arbitrary ValueError or shrink geometry to obtain a result. Primary
allocation, order, finalist selection, DSR/PSR/PBO/stability, lifetime accounting,
holdout scoring and gate predicates remain exact on measurable controls. No
diagnostic threshold or selector is added; longitudinal accounting-v14 stays.

These are family-local diagnostics. The winning family is still selected using
the whole search sample: its displayed diagnostic would not measure train-only
cross-family selection. Scores continue each fixed config's existing state and
internal turnover costs, without reconciling entry or switching trades for one
account. Static fundamental maps remain conditional supplied snapshots, never
historical point-in-time evidence. Report flags and active documentation must
carry these limits. Purged CV stays null and its count denotes geometry only.

This slice changes backend measurement and persistence only. The reduced
cross-sectional API projection and dashboard remain unchanged; no new public UI
claim is made. Historical rows are not backfilled. No generated data, frozen
cohort, calibration execution, threshold or workflow change is authorized here.

## Alternatives

1. Backend paired measurement first: chosen, useful durable evidence with narrow
   implementation scope and explicit historical attribution.
2. Add both evaluators at once: rejected until dependency spans and embargo
   semantics are derived and tested separately.
3. Persist only an unpaired family scalar: rejected; source drift can dominate
   raw Sharpe and old rows would lack method/geometry attribution.
4. Add full reports and configuration mappings or API/UI now: deferred as a
   separate publication slice; compact trial persistence matches current practice.

## Verification and reversal

Observe RED before source changes. Test full allocated family order, train-only
argmax and first-index ties, search-only same-row benchmark, actual geometry,
holdout exclusion, propagated measurement errors, legacy compatibility, complete
measured model invariants, immutable graph roundtrip and forged-copy refusal at
stores. Include Hypothesis selection/future-perturbation controls. Three frozen
deterministic prechange primary payloads must remain exact, excluding only new
diagnostic fields and run UUID/time. Baseline SHA256:
f54f294ef6976387060dabd2fa39dce2f67f5c65db2313a6060fbeec4d6ad096.
Independent final research review, foreground make check-all and exact master
CI precede completion. F265 remains open for purged evaluation and API publication.

Reverse by removing producer measurement and additive metadata together while
retaining support for already persisted measured rows; do not erase their record
or reinterpret historical scalars. A future selector, estimator, benchmark or
public publication change needs its own decision and evidence.
