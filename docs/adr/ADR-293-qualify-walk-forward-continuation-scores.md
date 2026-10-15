# ADR-293: State the walk-forward diagnostic's fixed-config continuation contract

- **Status:** Accepted
- **Date:** 2026-10-15
- **Deciders:** Codex autonomous peer under the standing charter
- **Addresses:** FINDING-246
- **Clarifies:** ADR-038, ADR-039, ADR-069
- **Preserves:** All executable arithmetic, averaging, selection, gates and accounting v14

## Context

ADR-038 specifies selecting a config on training rows and scoring that config's next-block return-column slice, then averaging the window Sharpes. The evaluator implements this specification. However, active descriptions imply that its score measures what a trading account periodically reselecting configs would earn, and causality is offered as sufficient justification for row-slice equivalence.

Each supplied engine column prices its own continuous holdings and internal turnover. Switching an account from one config's holdings to another can require different trades at the boundary. The return-only evaluator cannot reconstruct that turnover. A deterministic public-engine/public-evaluator example selects constant-long then constant-short and differs by exactly 20bp at the within-OOS switch under the existing engine convention. The comparison is a hypothetical position policy; the engine's normalized exposure/turnover approximation does not certify economic cash-and-units self-financing accounting. Zero-cost control agrees. This establishes a limitation of the executable-policy interpretation, not future-information leakage, incorrect implementation of the specified window statistic, universal Sharpe inflation or an actual graduate.

## Options considered

1. Qualify the existing diagnostic and preserve all values and historical attribution. Small, reversible, directly supported by evidence.
2. Silently subtract a fixed switch charge from existing return slices. Rejected: return-only evidence does not identify holdings, net switching turnover or timing; a universal charge is unjustified.
3. Replace the existing statistic with a self-financing stitched-policy estimator. Deferred: requires a separate position/capital/cost/timing/aggregation contract, public TDD and accounting/calibration governance. Not adopted here.
4. Leave wording unchanged because split selection is causal. Rejected: causal expert reward evaluation does not establish executable portfolio accounting.

## Decision

Describe existing WF output as train-selected fixed-config continuation-window scores. Each config's supplied path continues from its historical state; engine-supplied net returns include its internal turnover. The scores do not reconcile entry or switching trades for one account adopting successive configs. Past-only signals justify causal continuation, not independent flat-start backtests or a self-financing switched portfolio.

State that `mean_oos_sharpe` remains the equal mean of window Sharpes, not Sharpe on concatenated OOS returns. Do not characterize this intentional aggregation choice as an arithmetic defect. No separate WF floor gates graduation, but ADR-069's nondefault `select_by="walk_forward"` can rank families by the existing statistic; do not say it can never influence selection. Default observed selection remains.

Apply the reviewed scratch wording proposal with ADR-NEXT replaced by ADR-293 and FINDING-NEXT by FINDING-246 to the `WalkForwardResult` and `walk_forward_evaluate` docstrings, the active `_select_index` docstring, cold-memory §3 and architecture's active WF summary. Keep original ADR-038/039/069 historical text and all measured tables unchanged. Do not claim exhaustive cleanup of every historical or UI description. No new estimator, model field, threshold, route, selector behavior or accounting version.

F245 reported the prospective AR attempt incomplete and passed independent audit,
full local gate and exact CI before this decision. Fresh synchronization was
unchanged. No calibration is rerun or repriced for this wording qualification.

## Verification

The existing independent engine/evaluator probe is meaningful evidence; retain its repro and numbers in the finding. For the wording change, do not add tests that mirror text. Independently compare old/new Python ASTs after removing only the three changed leading docstrings: WalkForwardResult, walk_forward_evaluate and _select_index. Preserve every other docstring, node, import, constant, schema and executable statement exactly. Do not strip arbitrary string expressions or other constants.

Compare complete untouched gate, accounting, calibration, backtest-engine, original tests and frozen-file hashes; verify search/gate fingerprints remain identical. If the source provenance hash changes because docstrings changed, retain both executed revisions and distinguish code provenance from search/accounting identity. Do not claim the whole edited module's AST or source bytes are identical.

Run appropriate existing WF/search/report regressions, required full foreground `make check-all`, independent final scope/wording review, explicit-path individual commit/push and exact CI. No calibration/source rerun is required for this strictly numerical-behavior-preserving change; frozen measurements keep their executed identity and statistic meaning.

## Consequences and reversal

Readers can distinguish a causal window diagnostic from executable portfolio performance. Historical values and optional selector retain their meanings. A realized-policy estimator remains separate and unimplemented.

Reversal restores the prior active wording without numerical changes, while preserving the written finding; it would reopen the unsupported executable-policy implication.
