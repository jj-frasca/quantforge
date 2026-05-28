# Backtesting Spec (Cold Memory)

Formal contracts for the research engine (Phase 3). Read when working on
`backend/app/research/`. Decisions: ADR-007 (vectorized pandas/numpy, NOT vectorbt).
Behavioral rules live in CLAUDE.md; this holds shapes, formulas, and the oracle tests.

---

## 1. Price frame convention

Strategies and the engine operate on a pandas DataFrame, not raw PriceBars:

- **Index**: tz-aware UTC `DatetimeIndex`, ascending, unique.
- **Columns**: at least `close` (float). May include `open`/`high`/`low`/`volume`.
- Built from `list[PriceBar]` via `bars_to_frame(bars)` (uses adjusted `close`, as `float`).

`float` is used inside the engine (vectorized numpy math); `Decimal` is the storage/contract
type (PriceBar). The conversion happens once at `bars_to_frame`.

---

## 2. BaseStrategy contract

`app/research/strategies/base.py`. ABC:

- `generate_signals(data: pd.DataFrame) -> pd.Series`
  - returns a float position weight per bar, **in [-1.0, 1.0]** (−1 short … 0 flat … +1 long).
  - index MUST equal `data.index`.
  - **No look-ahead**: signal at time *t* may use only data up to and including *t*.
- `research_citations: list[str]` — non-empty; cite the real paper.
- `name: str`, `parameters: dict` (for the manifest's parameter hash).

Implemented strategies (see research-papers.md):
- `SMAStrategy` (fast/slow SMA crossover) — no external citation required.
- `MomentumStrategy` — Jegadeesh & Titman (1993).
- `MeanReversionStrategy` — Avellaneda & Lee (2010).

---

## 3. BacktestEngine (vectorized, ADR-007)

`app/research/backtesting/engine.py`. Pure pandas/numpy. Given `prices` (close series) and
`signals` (position weights), `initial_capital`, and `cost_rate` (fraction per unit turnover):

```
returns      = prices.pct_change().fillna(0)
position     = signals.clip(-1, 1)
# trade on the NEXT bar -> no look-ahead: yesterday's position earns today's return
gross        = position.shift(1).fillna(0) * returns
turnover     = position.diff().abs().fillna(position.abs())   # |Δposition| each bar
costs        = turnover * cost_rate
net          = gross - costs
equity_curve = (1 + net).cumprod() * initial_capital
```

`BacktestResult` (frozen): `equity_curve` (Series), `returns` (net Series), `metrics`
(`BacktestMetrics`), `n_trades` (count of nonzero turnover bars), `cost_rate`.

**Invariants** (Hypothesis): equity_curve all finite & > 0 for finite inputs; zero signal →
flat equity, zero trades; higher cost_rate → total return monotonically ≤.

---

## 4. Metrics

`app/research/backtesting/metrics.py` — `BacktestMetrics` (frozen):

- `sharpe`: `sqrt(252) * mean(net) / std(net)` (daily). 0.0 if std==0 (constant returns).
- `max_drawdown`: `min(equity/equity.cummax() - 1)` — **in [-1.0, 0.0]**. Positive = bug.
- `total_return`: `equity[-1]/equity[0] - 1`.
- `annualized_return`, `annualized_vol`: standard sqrt(252) scaling.

---

## 5. BenchmarkComparator

`app/research/benchmarks/comparator.py`. Default benchmark SPY. Given strategy `net` returns
and `benchmark` returns (aligned):

- `excess_returns = strat - bench`
- `information_ratio = sqrt(252) * mean(excess) / std(excess)`
- `beta = cov(strat, bench) / var(bench)`; `alpha = mean(strat) - beta*mean(bench)` (annualized)
- `tracking_error = sqrt(252) * std(excess)`
- `benchmark_relative_drawdown`: max drawdown of the excess equity curve.

**Oracle**: SPY vs SPY → excess≈0, IR≈0, alpha≈0, beta≈1.0 (ARCHITECTURE.md §8).
Never report an absolute Sharpe without benchmark context.

---

## 6. Monte Carlo (simulation/, NOT a strategy)

`app/research/simulation/monte_carlo.py`. GBM: `S_{t+1} = S_t * exp((mu - 0.5 sigma^2) dt +
sigma sqrt(dt) Z)`. Seeded RNG for determinism. **Invariant**: all path values > 0
(ARCHITECTURE.md §8 #8). Cite Black & Scholes (1973).

---

## 7. ExperimentManifest (lineage)

`app/research/backtesting/manifest.py`. Frozen, JSON round-trips with ALL fields preserved
(§8 #10): `experiment_id` (UUID), `created_at` (UTC), `git_commit_hash`, `strategy_name`,
`parameter_hash` (SHA256 of sorted params), `data_source`, `symbol`, `start_date`, `end_date`,
`data_quality_report_id`, `adapter_version`, `validation_config_hash`, `benchmark_symbol`.
Without it, a backtest result is not a reproducible scientific claim.

---

## 8. Oracle tests (must pass before any Phase 4 validation)

A sophisticated statistic on a buggy engine is worthless. All in `tests/`:
- `buy_and_hold_matches_analytic`: 100%-long signal → equity matches closed-form
  `initial * close/close[0]` (within 1e-9, zero cost).
- `zero_signal_produces_zero_exposure`: all-zero signals → flat equity, 0 trades, 0 Sharpe.
- `symmetric_long_short_neutrality`: +1/−1 alternating in a trend nets ≈ 0 (costs only).
- `transaction_cost_reduces_returns_monotonically`: costs=[0,.001,.005,.01] → returns non-increasing.
- `benchmark_comparator_spx_baseline`: SPY vs SPY → excess≈0, IR≈0, alpha≈0, beta≈1.
