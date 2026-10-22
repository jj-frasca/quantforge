# FINDING-292: Longitudinal lookback proxy retains a test-price-dependent training return

- **Status:** Confirmed; source-support limitation documented and active reporting qualified
- **Date:** 2026-10-21
- **Severity:** Medium — longitudinal source-support limitation
- **Reviewed revision:** `7f2a02b4a81146efd9391af71a974bcd2a015509`
- **Related:** ADR-039/198/293; FINDING-272/291

## Evidence

The shipped VolTargetedSMAStrategy can produce a retained purged-CV training
return that depends on a price in the test block, even when the split satisfies
the declared largest-integer-parameter embargo. This is a direct longitudinal
counterexample to complete-source-support interpretations of that proxy. It is
independent of FINDING-272's cross-sectional numerical-history witness.

For 300 finite positive closes `100+.02*r+sin(.7*r)` at ascending UTC daily
dates, change only price 99 from 102.16390880930635 to 102.66390880930635.
Use fast=2, slow=3, vol_window=21 and target_vol=0.01 with default engine cost_rate=0.001.
All prices 100..299 are identical between calls, and suffix position sizes are
unclipped. The public lookback proxy returns 21. The first split of 300 rows,
3 folds and embargo 21 tests 0..99 and retains training 121..299.

| Quantity | Original | Perturbed |
|---|---:|---:|
| Signal 120 | .13319618315607165 | .1380715941924408 |
| Retained net return 121 | -.0010287908800606063 | -.0010615809067590532 |

The retained net-return delta is -0.00003279002669844683. The corresponding gross
delta is -0.00002791461566207772 and turnover delta is 0.004875411036369182;
net uses the unchanged gross minus 0.001 times turnover convention.

Signal 120 sizes from log returns 100..120, including `log(price_100 / price_99)`.
Independent window-local arithmetic reconstructs both signal 120 values exactly
on the reviewed runtime. Engine return 121 holds signal 120; turnover 121 also
depends on signal 120. Thus this recipe's direct nominal price support reaches
`price_(t-22)`, beyond the max-parameter proxy 21. This is an operator-chain
endpoint/holding-lag issue, not merely rounding history.

## Boundary and causal controls

With only the splitter embargo increased to 22, training begins at 122 and the
directly dependent row 121 is excluded. The largest retained net difference
falls to 6.505213034913027e-19. It is not exactly zero: 168 retained rows differ
bitwise, including row 299. E22 removes this direct nominal overlap on this
recipe but does not certify exact computational source isolation or provide a
general fix. Remaining differences are consistent with rolling numerical
history; compiled reducer internals and arbitrary-length influence are not
established. No longitudinal selection amplification was tested.

For each price frame, public-engine runs on prefixes ending at 121 and 122 match
the corresponding complete-run positions and returns exactly. These bounded
controls distinguish dependence on earlier prices from future-information use;
they do not certify universal causality. No future-information leak is shown.

## Self-contained reproduction

Run from the isolated repository root using its locked backend environment:

```sh
PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
import numpy as np
import pandas as pd
from app.research.backtesting.engine import BacktestEngine
from app.research.strategies.vol_targeted_sma import VolTargetedSMAStrategy
from app.validation.purged_cv import lookback_embargo, purged_kfold_splits

r = np.arange(300, dtype=float)
idx = pd.date_range('2020-01-01', periods=300, tz='UTC', freq='D')
a = pd.DataFrame({'close': 100 + .02*r + np.sin(.7*r)}, index=idx)
b = a.copy(deep=True)
b.iloc[99, 0] += .5
assert np.flatnonzero(a.close.to_numpy() != b.close.to_numpy()).tolist() == [99]
s = VolTargetedSMAStrategy(fast=2, slow=3, vol_window=21, target_vol=.01)
e = BacktestEngine()
x, y = [e.run_strategy(f, s) for f in (a, b)]
assert lookback_embargo([s], floor=2) == 21
d = y.returns.to_numpy() - x.returns.to_numpy()
for gap in (21, 22):
    train, test = purged_kfold_splits(300, 3, embargo=gap)[0]
    assert [int(test[0]), int(test[-1])] == [0, 99]
    assert int(train[0]) == 100 + gap
    print('gap', gap, 'first train', train[0], 'max retained delta', abs(d[train]).max())
assert abs(d[121]) > 1e-8
for f, full in ((a, x), (b, y)):
    assert (abs(full.position.iloc[100:]) < 1).all()
    p = f.close.to_numpy()
    logs = np.log(p[100:121] / p[99:120])
    direction = np.sign(p[119:121].mean() - p[118:121].mean())
    local = direction * min(1., .01 / (logs.std(ddof=1) * np.sqrt(252)))
    assert local == full.position.iloc[120]
    for stop in (122, 123):
        short = e.run_strategy(f.iloc[:stop].copy(), s)
        pd.testing.assert_series_equal(full.returns.iloc[:stop], short.returns, check_exact=True)
        pd.testing.assert_series_equal(full.position.iloc[:stop], short.position, check_exact=True)
print('signal120', x.position.iloc[120], y.position.iloc[120])
print('net121', x.returns.iloc[121], y.returns.iloc[121])
print('pandas', pd.__version__, 'numpy', np.__version__)
PY
```

Runtime: Python 3.12.13, NumPy 2.5.4, pandas 3.0.6. Reviewed source SHA256:

- `vol_targeted_sma.py`: `e9d3561e2bc9e553bfcfdf813930be653fb2dc6858b5590b31ffd5d264ee61e2`
- Backtest `engine.py`: `1fe1afae4ddb3fb8b2d022a99653a2e168cb86ad52b911622be748687394fa6e`
- `purged_cv.py`: `e027ccd90bcdfe41e2647b0e0aac3915c669c6692b366f1f483b112ec00c7bf1`

Full scratch reproduction/receipt: `/tmp/qf-w43-s15-voltarget-pcv-support.py`
and `.json`; independent scope note: corresponding `.md`.
Only supplied deterministic prices and public strategy/engine/proxy/splitter
entry points were used. No RNG, source generator, search, calibration, provider,
broker, credentials, network or generated-data edit occurred.

## Reporting correction and boundaries

The three active purged docstrings are qualified: `purged_kfold_splits`,
`PurgedCVResult` and `lookback_embargo`. They distinguish declared row geometry
from complete source support, retain intentional later training, and remove the
unqualified current-catalog correctness claim. Active cold memory records this
longitudinal witness and the separate E22 numerical-history limit.
Existing ADR-039 already declares a proxy; its historical accepted text and
measurements remain intact. FINDING-291's residual PBO source wording stays a
separate later slice. No new embargo rule or numerical policy is adopted.

This establishes retained-return dependence for one supplied accepted class configuration;
it does not establish that the production catalog grid uses this configuration.
It does not establish statistical independence, score bias, an incorrect selected config, actual
production occurrence, a false graduate or a calibration rate. No purged
evaluator/search/gate comparison was run. Thresholds, estimator arithmetic,
fields, validation, serialized-result shape and accounting identity remain.
The Pydantic class docstring supplies the generated JSON-schema description:
its explanatory prose intentionally changes; schemas are not byte-identical.

## Verification

Parent and required independent research review reproduced the public-engine
witness, exact table, local signal reconstruction, four prefix controls and
E22 residual control (168 changed retained rows including row 299). All three
reviewed-revision source hashes match. The embedded reproduction is sufficient
without surviving scratch artifacts.

Existing PBO, purged-CV and walk-forward regressions passed: 152 tests in 8.00s.
Parent and independent AST comparisons preserve every node except the leading
docstrings of the three named definitions. Complete direct-model, nested-report
and OpenAPI schemas preserve every entry except the exact PurgedCVResult
description locations. The other 1,292 tracked backend/frontend/data paths
remain byte-identical. Gate fingerprint `25085698...493`, search fingerprint
`edb65cb5...459` and accounting v14 remain unchanged. The qualified source hash
is `8de9244b0d4eb742e3159827ebbef2c3f9ed98d8dfa05b4fe4bc432cfffefcdf`;
this documentation provenance differs from the reviewed source hash above.
Receipt: `/tmp/qf-w43-s15-f292-audit.json`.

Independent final scientific/content review approves the three-path scope.
Fresh foreground `make check-all PYTEST_WORKERS=2` passed: 13,811 backend
and 570 frontend tests, 97.38% backend and 97.83% frontend statement coverage,
plus lint, formatting and strict type checks. Receipt:
`/tmp/qf-w43-s15-check292.log`. Exact master CI is checked after publication.
No fresh cohort or calibration is needed for this strictly explanatory qualification.
