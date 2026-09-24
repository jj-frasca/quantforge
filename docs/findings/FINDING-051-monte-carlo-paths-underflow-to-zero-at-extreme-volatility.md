# FINDING-051: Monte Carlo GBM paths underflow to exactly 0.0 at extreme volatility

- **Severity:** Low
- **Status:** Resolved by ADR-123
- **Found:** 2026-09-24, autonomous session 104 (background audit of `backend/app/research/
  simulation/`, cold since 2026-07-01)
- **Affects:** `MonteCarloSimulator.simulate` (`app/research/simulation/monte_carlo.py`)

## Finding

`MonteCarloSimulator`'s own docstring claims "every factor is exp(...) > 0 and s0 > 0, [so] all
path values are strictly positive" — restated as ARCHITECTURE.md §8's required invariant #8 ("GBM
Monte Carlo paths: always positive"). True in exact real-number arithmetic; not always true in
float64. `simulate()` builds each path as `s0 * np.cumprod(exp(drift + diffusion), axis=1)`. For a
sufficiently extreme `sigma` (the only bound enforced is `sigma >= 0`, no upper limit) over enough
steps, the TRUE compounded value for a real fraction of paths falls below float64's smallest
representable double (~5e-324), and `np.cumprod` floors those entries to exactly `0.0`.

Verified this is genuine underflow of the true mathematical value, not a fixable precision loss from
`cumprod` specifically: recomputing the same paths via a cumulative sum of log-returns (numerically
stable across additions, unlike repeated multiplication) rescues only 8 of 9,175 zero-valued entries
in a `sigma=40, n_steps=252, n_paths=500, seed=1` run — the remaining 9,167 have a true cumulative
log-growth below `-744` (`log(5e-324)`), i.e. genuinely unrepresentable as any float64, not an
artifact of accumulation order.

`sigma=40` (4000% annualized volatility) is far outside any realistic equity or even
crypto/penny-stock range — no zero-valued entries appear until `sigma` exceeds roughly 30-35 at a
252-step horizon (confirmed: `sigma=20` at `n_steps=252` bottoms out at ~1.2e-110, still
representable). But `analyze_strategy_risk` (`app/research/simulation/risk.py`) derives `sigma`
from a strategy's realized daily-return standard deviation with no upper-bound validation, so a
sufficiently degenerate/pathological realized-return series (not necessarily a realistic one) could
reach this regime. The Hypothesis property test meant to guard invariant #8
(`test_gbm_paths_always_positive`) bounds `sigma` to `[0.0, 2.0]` at a fixed `n_steps=40` — nowhere
near where the failure lives — so it gave false confidence that the invariant held for the function's
actual validated input domain.

No downstream crash was found (`risk.py`'s `terminal_return`/`max_drawdown_per_path` both divide by
`paths[:, 0]`/`running_max`, which stay `>= s0 > 0`, so a zero-valued later entry produces a
well-defined `-1.0`, not `NaN`/`Inf`), but the documented invariant was false for inputs the
function's own validation accepts.

## Reproduction

```python
from app.research.simulation.monte_carlo import MonteCarloSimulator

paths = MonteCarloSimulator().simulate(s0=100.0, mu=0.0, sigma=40.0, n_steps=252, n_paths=500, seed=1)
(paths <= 0).sum()  # 9175 of 126500 entries, pre-fix
```
