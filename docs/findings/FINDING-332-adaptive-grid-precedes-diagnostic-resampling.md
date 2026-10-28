# FINDING-332: Adaptive grid selection precedes diagnostic resampling

- **Status:** Open for nested adaptive evaluation; reporting qualified by ADR-391
- **Date:** 2026-10-27
- **Reviewed revision:** 9f3d206f
- **Affected:** Longitudinal refined-grid WF/PCV and whole-search PBO interpretation

## Finding

run_search chooses its coarse family using full search-handle statistics and
centers refinement on that family's full-handle best config. It then validates
the realized refined grid on the same handle. The evaluator's train-row argmax
is past-only conditional on the supplied columns. Choosing which columns to
supply has already used later rows, including rows beyond early WF test windows.
Thus the refined diagnostic is not nested prequential evaluation of the entire
adaptive candidate-generation procedure. Even select_by="walk_forward" chooses
its coarse family using a mean spanning the whole search handle; the refinement
center still comes from the full-handle best concrete config.

PCV likewise evaluates a once-realized grid rather than rebuilding refinement
from each retained training set. Whole-search PBO correctly includes every
evaluated column under ADR-104, but CSCV partitions that realized return matrix;
it does not repeat adaptive grid construction inside each IS combination.
Adding all realized refined columns repairs F036's omitted-column defect without
making those columns independent of each resampled OOS block. No measured PBO
value or bias direction follows from this source observation alone.

## Bounded evidence

Use actual run_search orchestration, split_holdout, _score_configs, BacktestEngine,
refine_grid and space-filling allocation. Control the initial allocator to two
real SMA configs, (5,20) and (50,100), with refinement reserve 9. A validator stub
returns the actual coarse engine-score summary, then captures/stops at refined
validation. No gate, complete Experiment or graduation verdict is produced.
Independently evaluate the captured refined grids with the real engine and WF.

For 600 rows let b[t]=100*exp(0.0001*t+0.02*sin(t/9)). Both inputs use b outside
rows 200..347. Inside that slice use b[199]*exp(s*k), k=1..148, with s=0 or0.03.
The actual split has 348 search rows and 252 sealed rows. Both inputs' rows 0..199
and sealed rows 348..599 match exactly. Their earliest WF train 0..57/test 58..115
therefore sees identical source prices, all before the changed rows.

| Later-search suffix | Whole-search coarse center | Refined first-window choice | First-window OOS Sharpe |
|---|---|---|---|
| s=0 | fast 5 / slow 20 | fast 4 / slow 15 | 12.568504432728538 |
| s=0.03 | fast 50 / slow 100 | fast 38 / slow 75 | -5.2609617253935 |

Both actual refined grids contain 9 configs. Holding the first grid fixed on both
inputs preserves the COMPLETE first-window WF result dictionary exactly. Changing
the adapted grid changes that early selection and score. The paired control
isolates outer candidate-set adaptation from fixed-config source-row causality.
Parent and independent research each run the synthetic test successfully. These
are constructed accepted strategy classes under controlled allocation, not an
audit of standard allocated grids, actual production incidence or typical bias.
The earlier parent two-path default-SMA probe did not activate refinement; it is
a negative control, not supporting evidence for the table.

## Interpretation and limits

Call these fixed-realized-grid diagnostics. Train-only WF config selection does
not establish that the outer adaptive search could have constructed that grid
using only information available at the early train boundary. PCV already permits
later training observations; neither its row gap nor whole-search CSCV reconstructs
the outer adaptation. Fixed exogenous grids retain their conditional meaning.
F246's switching-account limitation and F272's numerical source-isolation limits
remain separate. No per-bar signal look-ahead is established by this witness.

The locked holdout is split before refinement and remains untouched and identical
in the witness. Selecting/refining on the search handle remains permitted; this
finding concerns the internal diagnostic's interpretation, not holdout leakage.
Matched whole-procedure null/power can still empirically measure the actual
adaptive procedure. Existing executed measurements retain their procedure and
meaning; this finding does not invalidate their observed composite rates.
No universal optimism, false graduate, threshold failure, measured PBO change,
historical pool impact or empirical improvement is established.

ADR-391 qualifies active descriptions without changing numbers, grids, allocation,
selection, gate thresholds, fingerprints or accounting-v14. Nested resampling
would need its own candidate-generation, budget, timing and scoring contract,
ADR/TDD and calibration identity review. No frozen cohort or generated record is
rerun, replaced or edited.

## Reproduction

Save the following as a scratch test and run it from backend with PYTHONPATH=.
and pytest -m "not live and not integration". No service or provider is used.

```python
from types import SimpleNamespace
import json
import numpy as np
import pandas as pd
import pytest
import app.research.lab.search as s
from app.research.strategies.sma import SMAStrategy
from app.validation.walk_forward import walk_forward_evaluate, walk_forward_splits

class StopAtRefined(Exception): pass

def test_outer_grid_uses_later_search_rows(monkeypatch):
    coarse=[SMAStrategy(5,20),SMAStrategy(50,100)]
    monkeypatch.setattr(s,'allocate_catalog_candidate_budget',lambda *a,**k:SimpleNamespace(families={'sma':coarse},refinement_reserve=9))
    captured=[]
    class Validator:
        def validate(self,name,configs,frame):
            if configs is not coarse and [x.parameters for x in configs] != [x.parameters for x in coarse]:
                captured.append((frame.copy(),configs))
                raise StopAtRefined()
            _,scores,*_=s._score_configs(configs,frame,s.BacktestEngine())
            return SimpleNamespace(strategy_name=name,observed_sharpe=max(scores),deflated_sharpe=0.,pbo=.5,parameter_stability_score=.5,walk_forward=None,purged_cv=None)
    monkeypatch.setattr(s,'ValidationEngine',Validator)
    t=np.arange(600);base=100*np.exp(.0001*t+.02*np.sin(t/9))
    for slope in (0.,.03):
        close=base.copy();close[200:348]=close[199]*np.exp(slope*np.arange(1,149))
        frame=pd.DataFrame({k:close for k in ('open','high','low','close')},index=pd.date_range('2020-01-01',periods=600));frame['volume']=1000.
        with pytest.raises(StopAtRefined):s.run_search(frame,'SYN',['sma'],refine=True)
    (a,ga),(b,gb)=captured
    pd.testing.assert_frame_equal(a.iloc[:200],b.iloc[:200])
    assert len(a)==len(b)==348
    assert [c.parameters for c in ga] != [c.parameters for c in gb]
    split=walk_forward_splits(348,5)[0]
    assert split[1][-1]<200
    receipts=[]
    for frame,grid in captured:
        performance=np.column_stack([s.BacktestEngine().run_strategy(frame,c).returns.to_numpy() for c in grid])
        wf=walk_forward_evaluate(performance,[split])
        selected=wf.splits[0].selected_config
        receipts.append({'grid':[c.parameters for c in grid],'early_selected':grid[selected].parameters,'early_oos':wf.mean_oos_sharpe})
    fixed=[]
    for frame in (a,b):
        matrix=np.column_stack([s.BacktestEngine().run_strategy(frame,c).returns.to_numpy() for c in ga])
        fixed.append(walk_forward_evaluate(matrix,[split]).model_dump())
    assert fixed[0]==fixed[1]
    assert receipts[0]['early_selected']!=receipts[1]['early_selected']
    print(json.dumps({'train':[int(split[0][0]),int(split[0][-1])],'test':[int(split[1][0]),int(split[1][-1])],'changed_search_rows':[200,347],'receipts':receipts}))
```

## Verification of the reporting change

Parent and independent research verify two complete module ASTs after removing
only the four named leading docstrings, 496 untouched app/test source hashes and
unchanged search/gate fingerprints. Both verify the actual WalkForwardResult
JSON Schema matches its parent except root description prose. No field,
constraint or serialized-result shape changes. Both existing WF/count/search/PCV
regression runs pass 186 tests. Research independently extracts the reproduction
from this finding and runs it successfully, then approves all seven paths.
Required foreground full gates and exact post-push CI receipts are recorded in
CODEX_RUNNING_STATE. No failing-test claim applies to this numerical-behavior-
preserving wording unit.

## Session 10 addendum: unchanged single-family allocation

A second bounded control uses the unchanged allocator, default n_per_param=3,
default GateConfig and actual ValidationEngine coarse validation for a requested
single SMA family. It does not claim the full default catalog or production
prevalence. Both paths use the same seven actual coarse configs:
(1,2), (1,251), (1,500), (100,251), (100,500), (200,251), (200,500).

Keep the 600-row base above, but change only search prices 200..347 to b[199]
for the flat arm, or b[199]*exp(0.3*(k%2)), k=0..147, for the alternating arm.
The early 200 prices and 252 sealed prices match exactly. The complete actual
coarse first-window WF dictionaries match, with OOS 22.933345297737414.

The flat arm's coarse winner is (1,2), giving only one raw refined config; the
existing minimum-two rule skips refined validation. The alternating arm chooses
(100,251), producing nine refined configs and entering the second validation call.
A wrapper calls the actual validator on the coarse grid, then captures/stops
BEFORE evaluating the alternating refined grid. The flat arm completes the
ordinary search. No gate-passage or outcome comparison is made. This demonstrates
future-search dependence of refinement-branch existence with the unchanged
allocator for this request; it supplies no new refined WF/PBO value comparison.
The earlier controlled-allocator score-change table retains its stated scope.

Parent and independent research reproduce matching JSON receipts; research also
checks the actual allocator, scoring and raw refinement counts separately. No
runtime, threshold, schema or identity change follows. Existing ADR-391 governs
this additional evidence; no new decision or TDD implementation claim is made.

Self-contained scratch reproduction (run with PYTHONPATH=. from backend):

```python
import json
from unittest.mock import patch
import numpy as np
import pandas as pd
import app.research.lab.search as search
from app.validation.engine import ValidationEngine

class Captured(Exception):
 pass
original=ValidationEngine.validate
receipts=[]
frames=[]
x=np.arange(600)
base=100*np.exp(.0001*x+.02*np.sin(x/9))
for kind in ('flat','alternate'):
 prices=base.copy()
 prices[200:348]=prices[199]*(1.0 if kind=='flat' else np.exp(.3*(np.arange(148)%2)))
 frame=pd.DataFrame({'close':prices},index=pd.date_range('2020-01-01',periods=600))
 frames.append(frame)
 calls=[]
 def capture(self,name,configs,data):
  calls.append({'configs':[c.parameters for c in configs]})
  if len(calls)==2:raise Captured()
  result=original(self,name,configs,data)
  calls[-1]['observed']=result.observed_sharpe
  calls[-1]['wf_first']=result.walk_forward.splits[0].model_dump()
  return result
 with patch.object(ValidationEngine,'validate',capture):
  try:
   result=search.run_search(frame,'SYN',['sma'],refine=True)
   status='completed-no-refined-grid'
  except Captured:
   status='captured-refined-grid-before-evaluation'
 receipts.append({'kind':kind,'status':status,'calls':calls})
pd.testing.assert_frame_equal(frames[0].iloc[:200],frames[1].iloc[:200])
pd.testing.assert_frame_equal(frames[0].iloc[348:],frames[1].iloc[348:])
assert receipts[0]['calls'][0]['configs']==receipts[1]['calls'][0]['configs']
assert receipts[0]['calls'][0]['wf_first']==receipts[1]['calls'][0]['wf_first']
assert len(receipts[0]['calls'])==1 and len(receipts[1]['calls'])==2
assert len(receipts[1]['calls'][1]['configs'])==9
print(json.dumps(receipts,indent=2))
```

Independent research extracts this second code block from the finding and runs it
successfully: all prefix, sealed-tail, coarse-grid, early-WF and branch assertions
pass, with output exactly matching the original JSON receipt. Final review
approves this one-path evidence extension. Required full-gate and post-push CI
receipts are recorded in the session ledger.
