# FINDING-293: Infinite aligned signals publish finite backtest performance

- **Status:** Confirmed deterministic witness; Resolved by ADR-343 — aligned infinity refuses before clipping
- **Date:** 2026-10-21
- **Severity:** Medium — invalid strategy evidence becomes full directional exposure
- **Reviewed engine revision:** `d3b464db3f97c1aad665d0123afbdb3c2d3afd7e`
- **Related:** ADR-007/176/177/178/260/265/339; FINDING-109/209/214/287

## Evidence

BacktestEngine.run reindexes signals, clips to [-1,1], and fills missing weights
with zero. Clipping converts positive/negative infinity to full long/short
exposure before finite return/equity checks. Valid source prices and finite
reported wealth therefore do not certify validity of the original aligned
strategy observations.

Use three ascending UTC daily prices [100,110,121], initial_capital=100000 and
cost_rate=0.001. Only the supplied first signal differs between calls:

| First signal (others zero) | Published positions | Total return | Stored Sharpe |
|---|---|---:|---:|
| +Inf | [1,0,0] | .09790100000000002 | 9.026641375381294 |
| -Inf | [-1,0,0] | -.10189900000000007 | -9.301599352786084 |

Positive-infinity net returns are [-.001,.09900000000000009,0] and equity is
[99900,109790.10000000002,109790.10000000002]. Each infinite-input payload
matches its finite +/-2 clipping control. The stored metrics are evidence of
invalid input reaching publication, not an investment-performance inference.
Final-only infinity [0,0,Inf] also publishes finite metrics and initial turnover
at that final row, with total return -.0010000000000000009.

No actual catalog strategy output, corrupt historical experiment, false
graduate, trading order or market effect is established. The supplied-data
fixture is not a calibration or source-generator measurement.

## Self-contained historical-behavior reproduction

From the isolated repository root with its locked backend environment:

```sh
PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
import numpy as np
import pandas as pd
import subprocess
import app.research.backtesting.engine as engine_module

# Run only the recorded historical engine source in memory; no checkout or edits.
revision = 'd3b464db3f97c1aad665d0123afbdb3c2d3afd7e'
source = subprocess.check_output(
    ['git', 'show', revision + ':backend/app/research/backtesting/engine.py'], text=True)
namespace = dict(vars(engine_module))
exec(compile(source, 'historical_backtest_engine.py', 'exec'), namespace)
BacktestEngine = namespace['BacktestEngine']

p = pd.Series([100.,110.,121.],
    index=pd.date_range('2020-01-01', periods=3, tz='UTC'))
e = BacktestEngine(cost_rate=.001)
for value in (np.inf, -np.inf, 2., -2., np.nan):
    s = pd.Series([value,0.,0.],index=p.index)
    out = e.run(p,s)
    assert np.isfinite(out.equity_curve).all()
    print(value, out.position.tolist(), out.returns.tolist(),
          out.equity_curve.tolist(), out.metrics.total_return, out.metrics.sharpe)
wide = pd.Series([np.longdouble(np.finfo(float).max)*2,0,0],
                 index=p.index, dtype=np.longdouble)
assert np.isfinite(wide.iloc[0])
assert not wide.isin([np.inf,-np.inf]).any()
print('native-wide finite positions',e.run(p,wide).position.tolist())
print('pandas',pd.__version__,'numpy',np.__version__)
PY
```

Runtime Python 3.12.13 / NumPy 2.5.4 / pandas 3.0.6. Reviewed engine SHA256:
`1fe1afae4ddb3fb8b2d022a99653a2e168cb86ad52b911622be748687394fa6e`.
Scratch current-behavior reproduction and receipt:
`/tmp/qf-w43-s15-engine-infinite-signal-audit.py` and `.json`.
Scratch prospective guard audit and scope:
`/tmp/qf-w43-s15-engine-aligned-infinity-proposal-audit.py`, `.json`, `.md`.

## Selected correction and compatibility boundary

ADR-343 adopts only exact signed infinity refusal after the original reindex
and before the original clipping/filling. Existing price/calendar checks and
returns calculation retain their order. Bind the aligned Series once, inspect
native `isin([np.inf,-np.inf]).any()`, then keep the original clip/fill path.
No float64 conversion, broad dtype/range policy or NaN refusal is introduced.

Aligned first/interior/final/singleton infinity refuses, including with zero
cost. Unmatched infinity remains discarded by reindex; empty price histories
with unmatched infinity retain empty output. This certifies only the selected
aligned infinity boundary, not complete original-signal validity or causality.

Independent scratch comparison covered 28 supplied-signal cases plus four
boundary controls. Unflagged accepted positions/returns/equity, native dtypes,
metrics, n_trades and cost_rate were exact. This includes NaN warmup, nullable
Float64/pd.NA, sparse alignment, native/nullable integers, float32, fractional
weights, signed zero, finite saturation, explicit finite float128 beyond
binary64 range, empty signals and unmatched infinity. The native-wide fixture
explicitly asserted original finiteness and dtype; implicit Series inference
would otherwise narrow its supplied value before the engine.

Unflagged unsupported bool/nullable bool, string/'inf' string, numeric-object,
Fraction-object, Decimal-object and finite complex inputs retain their existing
native exception type/message. Decimal Infinity and complex(inf,0) already
failed but match the new predicate, changing refusal timing/message. No full
error/warning equivalence is claimed for these flagged unsupported inputs.
Malformed-price/calendar precedence remains exact.

F287/ADR339 concerns latest paper sizing and refuses all nonfinite converted
latest values; it does not override backtest warmup/missing-to-flat behavior.
F209/ADR260 and F214/ADR265 concern cross-sectional original-source ranking/IC
boundaries. F109/ADR177 protects finite scaled wealth; it cannot recover
infinity erased by clipping. This finding concerns a distinct public-engine
publication boundary, for which targeted existing-finding checks found no fix.

The invalid-input success domain narrows: callers that formerly completed may
now error. `run_search` propagates the ValueError from `_score_configs`.
The `measure_power` and `calibrate_gate` loops catch per-symbol ValueError,
record an error and continue; their successful-experiment count supplies the
completed `n_symbols` denominator, and all-error batches refuse. Consequently
completed error denominators may differ if these inputs occur. Unchanged finite formulas or
fingerprints do not prove unchanged rates. No such production occurrence or
changed rate is measured. Preserve finite estimator arithmetic, thresholds,
fields and accounting-v14 identity; verify current search/gate fingerprints.
The edited source provenance changes. Frozen results retain their executed
identity without replay, redraw, repair or relabeling.

## Verification status

F292 exact CI and fresh synchronization completed before ADR-343 adoption.
Actual repository precode TDD: 33 refusal cases failed while 10 compatibility
controls passed, with no engine source diff. The aligned-only guard then passed
all 248 focused engine tests, including 43 new cases and two Hypothesis
properties. Ruff, formatting and targeted mypy passed. The initial Ruff check
identified two regex raw-string annotations, corrected without runtime changes.

Actual parent-versus-implementation comparisons preserve complete accepted
payloads/dtypes and unflagged errors across the 32 audited cases/controls.
The historical reproduction above loads only the recorded engine source in
memory, so it continues to demonstrate the pre-fix behavior after this guard.
Receipt: `/tmp/qf-w43-s15-engine-aligned-infinity-final-audit.json`;
independent receipt: `/tmp/qf-w43-s15-engine-aligned-infinity-ACTUAL-final-review.json`.
Independent final five-path review approves the runtime, tests and corrected
historical reproduction. Whole prior engine AST is preserved except the exact
class-doc line and declared reindex/guard/position-operand transformation.
All original tests and the other 1,292 tracked backend/frontend/data paths
remain byte-identical. Full direct/report/OpenAPI schemas and search/gate
fingerprints match the post-F292 parent. Engine source provenance is now
`062893b8238df762ad6b320330746c49962c98a7458ef368606176ebe27bbcc2`.
Receipt: `/tmp/qf-w43-s15-engine-ast-audit.json`.
Fresh full foreground `make check-all PYTEST_WORKERS=2` passed: 13,854
backend tests, 570 frontend tests, 97.38% backend and 97.83% frontend statement
coverage, plus lint, formatting and strict types. Receipt:
`/tmp/qf-w43-s15-check343.log`. Exact master CI is verified after publication.
No RNG, source generator, search, calibration, provider, broker, credentials
or network was used in the scientific verification.
