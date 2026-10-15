# FINDING-246: Walk-forward continuation slices do not price a switched account

- **Status:** Confirmed interpretation limitation; active qualification adopted
- **Date:** 2026-10-15
- **Scope:** Interpretation of ADR-038 window-return diagnostic
- **Decision:** ADR-293

## Evidence

`ValidationEngine.validate` backtests each config once and supplies the full-history net-return matrix to `walk_forward_evaluate`. The latter selects the train-block Sharpe argmax and scores that column's forward rows. This correctly computes the statistic specified by ADR-038, including supplied per-config internal turnover. It does not reconcile holdings when a trading account adopts a different config.

Independent reproduction: `/tmp/qf-w42-s17-wf-scope-audit-v2.py`.
Receipt: `/tmp/qf-w42-s17-wf-scope-audit-v2.json`, SHA256
`a98f8be6da9a89770ac6998dd083dd7c0d49faa2170ff657a59d1e523065f416`.
The session15 investigation and its original receipts remain preserved; their
unqualified account labels are not a certification of economic self-financing.

The independent deterministic fixture uses the public engine, public split generator and evaluator, twelve manually specified prices and hypothetical constant-long/constant-short causal configs. It uses no RNG, catalog generator, search, calibration or frozen outcome content.

Nominal price returns are `[0,.01,.02,.015,-.04,-.03,-.025,-.035,.005,-.004,.003,-.002]`. Training `[0..3]` selects long for tests `[4..7]`; expanding training `[0..7]` selects short for tests `[8..11]`. Under the existing close-execution convention, the selected next-block config becomes known at close3/close7 from training data then available.

A hypothetical position policy under the existing engine convention changes +1 to −1 at close7. The engine charges `.001*abs(−1−1)=.002` switching cost on row7, inside the first OOS block. The selected long-column return there is approximately `−.035`; the hypothetical policy's modeled return is `−.037`. Every other OOS return agrees to floating rounding. This does not rely on excluding the separate initial entry cost at close3, which precedes the test rows. Cost_rate0 control makes the selected-slice and hypothetical-policy OOS returns agree exactly. The engine's normalized position/turnover model does not certify exact cash-and-units self-financing accounting.

Causal individual signal histories permit continuous fixed-config continuation; they do not make a return-only slice account for a different position path's trades. The evaluator has neither holdings nor a cost/timing contract from which to infer those trades. Other fixtures can have different boundary relationships; a universal fee or one-direction Sharpe adjustment is not established.

## Claims that remain distinct

- No look-ahead leakage is shown: each selection uses preceding train rows. Carrying causal signal history is not itself leakage.
- The equal mean of window Sharpes is ADR-038's deliberate definition, not Sharpe on stitched OOS returns. Even at zero costs the fixture's mean-window Sharpe is `−40.907305759937394`, versus approximately `−14.688270252785616` for the concatenated slices.
- Missing a loss does not imply universal Sharpe inflation. Here the reported mean-window Sharpe is `−40.907305759937394`; the hypothetical policy's same-window mean is `−39.5635779041669` because the additional loss changes dispersion. This example is evidence about return accounting, not an optimistic-Sharpe bound.
- Purged CV (ADR-039) is deliberately a noncausal resampling diagnostic, not a live simulation. No stitched trading-policy correction is proposed for it.
- No separate WF threshold gates graduation, but nondefault ADR-069 `select_by="walk_forward"` ranks families by this statistic. Default observed selection is unchanged. No actual catalog switching prevalence, pool effect, false graduate or empirical calibration impact was measured.

## Qualification and verification

Qualify active docstrings/cold memory/architecture to name train-selected fixed-config continuation-window scores, internal-cost inclusion, missing switched-account reconciliation and equal-window Sharpe aggregation. Retain all executable arithmetic, averaging, fields, default/nondefault selector behavior, gate thresholds, accounting v14 and historical measurement attribution. Original ADR-038 remains unchanged.

Exact proposed edits: `/tmp/qf-w42-s15-wf-qualification-proposal.diff`; structured anchors: `/tmp/qf-w42-s15-wf-qualification-proposal.json`. Source edits are docstrings only. Compare executable ASTs after removing only the three changed leading docstrings (WalkForwardResult, walk_forward_evaluate and _select_index), preserving every other docstring/node. Also verify untouched component/test/frozen hashes and fingerprints. No text-mirroring tests are proposed. Existing meaningful probe, existing regressions, independent review and required foreground full gate/CI remain required before delivery.

This is a limitation of interpreting the current diagnostic as a self-financing reselection policy. A separate realized-policy estimator would require a future ADR, exposures and timing evidence, public TDD and accounting/calibration review; none is adopted here. Scope is not universal cleanup of historical text or all frontend descriptions.

Session17 independently reproduced the manual policy arithmetic and both cost
controls before adoption. F245 exact CI38774449953/hooks38774449806 passed,
and a fresh clean fetch/rebase was unchanged. Final independent six-file review approved the scientific wording and exact
four-target manifest with ADR/FINDING number substitutions. Independent AST
comparison removed only the three named docstrings; every other node and
docstring was exact. Parent guard verified all other tracked components and
tests, every frozen AR artifact hash, search/gate fingerprints and accounting
v14 unchanged. Receipts: `/tmp/qf-w42-s17-final293-review.json` and
`/tmp/qf-w42-s17-guard293.json`. Edited source bytes and provenance hashes do
change with docstrings; earlier measurements retain their executed revisions.

Full foreground `make check-all` passed 11,376 backend tests (97.34% coverage)
and 363 frontend tests (97.63% statement coverage), including existing
walk-forward, search and reporting regressions. Lint, formatting and strict
typing passed. The permanent reproduction below was also executed successfully.
No implementation change or prose-mirroring test is introduced.
## Reproduce the position-policy difference

The example uses the existing normalized exposure and turnover convention,
without certifying cash-and-units self-financing. Run from backend with installed dependencies.

```python
import numpy as np
import pandas as pd
from app.research.backtesting.engine import BacktestEngine
from app.validation.walk_forward import walk_forward_evaluate, walk_forward_splits

r = np.array([0, .01, .02, .015, -.04, -.03, -.025, -.035,
              .005, -.004, .003, -.002])
index = pd.date_range('2020-01-01', periods=12, freq='B', tz='UTC')
prices = pd.Series(100 * np.cumprod(1 + r), index=index)
splits = walk_forward_splits(12, 2)
# Enter at close3; reverse at close7; retain final position, no liquidation.
policy = pd.Series([0, 0, 0, 1, 1, 1, 1, -1, -1, -1, -1, -1], index=index)
for cost in (.001, 0):
    engine = BacktestEngine(cost_rate=cost)
    matrix = np.column_stack([
        engine.run(prices, pd.Series(sign, index=index)).returns.to_numpy()
        for sign in (1., -1.)
    ])
    result = walk_forward_evaluate(matrix, splits)
    assert [s.selected_config for s in result.splits] == [0, 1]
    selected = np.r_[matrix[4:8, 0], matrix[8:12, 1]]
    modeled = engine.run(prices, policy).returns.to_numpy()[4:]
    expected = np.zeros(8)
    expected[3] = 2 * cost  # Original row7, inside first OOS block.
    np.testing.assert_allclose(selected - modeled, expected, rtol=0, atol=1e-15)
    if cost == 0:
        np.testing.assert_array_equal(selected, modeled)
```
