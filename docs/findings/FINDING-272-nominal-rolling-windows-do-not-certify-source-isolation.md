# FINDING-272: Nominal rolling windows do not certify numerical source isolation

- **Date:** 2026-10-19
- **Severity:** Medium — prospective dependency/embargo proof limitation
- **Status:** Confirmed; documented limitation, cross-sectional PCV still unmeasured
- **Reviewed revision:** 1773a717
- **Related:** FINDING-265; ADR-024/039/104/198/291/293/321/322

## Evidence

Changing one old price changes late signals and portfolio returns from two
shipped cross-sectional factors, even though every price in the late return's
nominal expression window is identical. A nominal rolling length therefore
cannot certify exact computational source isolation for these factors.

The deterministic 500-by-3 Float64 price panel has columns A/B/C and the same
unique ascending RangeIndex in both calls. At integer row r,
A=B=100+0.03*r+sin(0.73*r), C=1.03*A. Only price (row 1, A) changes:
100.6968696350037 becomes 100696.86963500369. All prices are finite and positive;
public portfolio returns are complete and finite. The large old perturbation
is an adversarial witness, not a claim about ordinary market prevalence.

The shipped registry factories feed public portfolio_returns with quantile 0.2
and cost_rate 0.001. On pandas 3.0.6, both NumPy 2.5.3 (initial reproduction)
and the current locked NumPy 2.5.4 reproduce these values exactly:

| Family/config | Observation | Original | Changed |
|---|---|---:|---:|
| xs_low_volatility, vol_window=21 | A signal, row 499 | -0.004456365341710916 | -0.004456365582176331 |
| same | portfolio return, row 473 | -0.003999999999999778 | -0.002 |
| xs_risk_adjusted_momentum, lookback=63 | A signal, row 499 | 0.08316152371126764 | 0.08316153276008342 |
| same | portfolio return, row 499 | -0.004000000000000222 | -0.002 |

The low-volatility signal expression uses 21 returns, reaching 21 price rows
back. Its net portfolio return additionally depends on previous target weights,
so row 473's nominal price support is [451,473] inclusive. Risk-adjusted
momentum's analogous signal/return lags are 63/64; row 499's nominal price
support is [435,499]. Both complete support windows match exactly between the
panels; changed row 1 is far outside them.

Near ties can turn small numerical signal differences into different ranked
holdings. Independent inspection at those two return rows finds turnover
charges of 0.004 originally versus 0.002 after the old-cell perturbation;
the gross terms are at rounding scale. Thus the difference reaches the public
portfolio output, rather than only a displayed score. No general sign or
magnitude of the effect is asserted.

## Self-contained reproduction

Run from the repository root with its locked backend environment:

```sh
PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
import numpy as np
import pandas as pd
from app.research.cross_sectional.engine import portfolio_returns
from app.research.cross_sectional.registry import default_strategies

r = np.arange(500, dtype=float)
v = 100 + 0.03 * r + np.sin(0.73 * r)
p = pd.DataFrame({'A': v, 'B': v, 'C': 1.03 * v})
q = p.copy()
q.loc[1, 'A'] *= 1000
assert np.argwhere(p.to_numpy() != q.to_numpy()).tolist() == [[1, 0]]
assert p.index.equals(q.index) and p.columns.equals(q.columns)
assert p.index.is_unique and p.index.is_monotonic_increasing
for prices in (p, q):
    assert np.isfinite(prices.to_numpy()).all()
    assert (prices.to_numpy() > 0).all()

registry = default_strategies()
for name, params, row, lag in (
    ('xs_low_volatility', {'vol_window': 21}, 473, 22),
    ('xs_risk_adjusted_momentum', {'lookback': 63}, 499, 64),
):
    signal = registry[name].build(params)
    a, b = signal(p), signal(q)
    x = portfolio_returns(a, p, quantile=0.2, cost_rate=0.001)
    y = portfolio_returns(b, q, quantile=0.2, cost_rate=0.001)
    assert np.isfinite(x.to_numpy()).all() and np.isfinite(y.to_numpy()).all()
    assert row - lag > 1
    assert p.iloc[row-lag:row+1].equals(q.iloc[row-lag:row+1])
    assert a.loc[499, 'A'] != b.loc[499, 'A']
    assert x.iloc[row] != y.iloc[row]
    # Bounded causal controls: future rows do not change earlier results.
    for stop in (100, 250, 400):
        prefix = p.iloc[:stop]
        short_signal = signal(prefix)
        pd.testing.assert_frame_equal(a.iloc[:stop], short_signal, check_exact=True)
        pd.testing.assert_series_equal(
            x.iloc[:stop],
            portfolio_returns(short_signal, prefix, quantile=0.2, cost_rate=0.001),
            check_exact=True,
        )
    print(name, a.loc[499, 'A'], b.loc[499, 'A'], x.iloc[row], y.iloc[row])
print('pandas', pd.__version__, 'numpy', np.__version__)
PY
```

Source SHA256 at review:

- strategies.py: ef0c1745a301f10cd828b6e9045e797978b8594bb974f503b58169b06bbe40c2
- engine.py: 9b0cc15a7cd170a52e15c9d13cb3318ae4ee1358be1eb5240b8e63d378838d16
- registry.py: 743579f129b46fa059dab5af9db052a2ea090b7a5f9d8e2e8db53b2b8216e68f

The original scratch probe and richer receipt remain at
/tmp/qf-w43-s1-xs-rolling-support-probe.py/json; parent current-runtime receipt:
/tmp/qf-w43-s3-xs-support-current.json. The executable block above retains the
essential witness without depending on scratch-file survival.

## Scope and disposition

This is consistent with accumulated numerical state in rolling reductions.
Compiled reducer internals were not audited, and arbitrary-length influence
is not proved. No future information is used by this witness: old prices affect
later outputs. Bounded full-prefix controls agree exactly, distinguishing
causality from finite-window isolation without proving universal causality.
No arbitrary exact-rank contract is inferred from floating arithmetic.

Current cross-sectional search imports only purged_kfold_splits, records
geometry counts and leaves purged_cv null. No existing cross-sectional PCV
score is shown wrong. No production occurrence, false graduate, longitudinal
PCV/EMA impact, calibration bias or statistical significance is established.

FINDING-265 remains open for cross-sectional purged evaluation. A future
integration ADR must explicitly choose its isolation basis: nominal expression
windows with the numerical-history limitation disclosed, independently audited
window-local arithmetic, or a restricted supported-family policy. This finding
does not adopt any of those designs. A maximum-grid-integer shortcut also misses
hidden defaults and combined windows; it cannot substitute for operator-chain
analysis. Different family embargoes may retain different folds, so benchmark
pairing must follow actual kept test rows. Static fundamental snapshots still
lack historical point-in-time availability; price embargoes cannot repair that.

No factor arithmetic, ranker, evaluator, selector, threshold, accounting identity,
catalog, generated record or frozen cohort changes. Altering factor outputs
would require separate methodology/identity governance and test-first evidence.

## Verification

Parent and required independent research-expert reproduction confirmed the
witness and bounded causal controls. Independent final review approved both
documentation paths and reran the exact embedded reproduction on the locked
NumPy 2.5.4 environment. Fresh foreground make check-all PYTEST_WORKERS=4 passed:
13,085 backend tests (97.41% coverage), 479 frontend tests (97.72% statements),
lint, formatting and strict types. Log: /tmp/qf-w43-s3-check272.log. All local
checks closed successfully; exact master CI is verified after publication.
Backend, frontend, tests and generated data retain their tracked bytes.
