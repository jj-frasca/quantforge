# API Contracts (Cold Memory)

FastAPI endpoint specifications. Read when working on `backend/app/api/`. Endpoints are
versioned under `/api/v1`. Response bodies are Pydantic models (auto-documented at `/docs`).

Phase 5 will expand this (data explorer, strategy config, backtest results). The validation
endpoint below ships first because the ValidationReport is the MVP deliverable.

---

## GET /health
Liveness probe. → `200 {"status": "ok", "environment": "<env>"}`. No DB dependency.

---

## GET /api/v1/strategies
Return the strategy catalog — the single source of truth for what `/backtest` and
`/validate` accept, including UI labels, descriptions, citations, parameter schemas, and
category tags. Drives the dynamic strategy form on the frontend (ADR-010).

**Responses**:
- `200` → `list[StrategySchema]`:
  ```json
  [
    {
      "name": "sma",
      "label": "SMA Crossover",
      "category": "Trend",
      "description": "Long when the fast SMA crosses above the slow; short below ...",
      "citations": ["..."],
      "parameters": [
        { "name": "fast", "type": "int", "default": 20, "minimum": 1, "maximum": 200,
          "label": "Fast window", "description": "..." },
        { "name": "slow", "type": "int", "default": 50, "minimum": 2, "maximum": 500,
          "label": "Slow window", "description": "..." }
      ]
    }
  ]
  ```
  - `category` is a backend `Literal["Trend" | "Mean Reversion" | "Breakout" |
    "Combination"]`. The frontend groups the dropdown by category via `<optgroup>`.
    Adding a new category requires extending the Literal AND the frontend Zod enum in
    the SAME commit — otherwise every new-category strategy fails the boundary parse
    (see [[feedback-frontend-shadow-validators]]).
  - `parameters[].type` is `"int" | "float"`; `default`, `minimum`, `maximum`, `step`
    drive the rendered numeric input.

---

## GET /api/v1/bars
Return cached price bars for a `(symbol, range)` — pure read, **does not trigger ingestion**.
Powers the Data Explorer chart and any future "show what's stored" UIs.

**Why sync**: plain `def` threadpooled by FastAPI; the blocking repository read is in the
threadpool (ADR-009).

**Query parameters**:
- `symbol` (string, ≥1 char)
- `start_date` (ISO-8601 datetime)
- `end_date` (ISO-8601 datetime)

**Responses**:
- `200` → `BarsResponse`:
  ```json
  {
    "symbol": "AAPL",
    "n_bars": 2,
    "bars": [
      { "timestamp_utc": "2024-01-01T00:00:00Z",
        "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 1000000 }
    ]
  }
  ```
  Empty array + `n_bars=0` when nothing is cached (not a 404 — "no data" is a normal answer).
- `ChartBar` is a slim float projection of the canonical `PriceBar`. Decimal precision is
  preserved in storage / backtesting; the API boundary converts because charts don't need it.

**DI**: `get_repository` only. The data adapter is intentionally NOT injected — this endpoint
must never silently call out to a vendor.

---

## POST /api/v1/ingest
Run the `DataIngestionPipeline` for a `(symbol, range)` and return the result + quality
report. Bars are stored in the `PriceBarRepository` (TimescaleDB in prod) only when the
quality gate passes; the report is always persisted.

**Why sync**: plain `def`, threadpooled by FastAPI — blocking yfinance + sync DB calls don't
stall the event loop (ADR-009).

**Request** (`IngestRequest`):
```json
{
  "symbol": "AAPL",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date":   "2024-12-01T00:00:00Z"
}
```

**Responses**:
- `200` → `IngestResponse`:
  ```json
  {
    "symbol": "AAPL",
    "bars_ingested": 230,
    "stored": true,
    "quality_report": { "symbol": "AAPL", "checked_at": "...", "issues": [], "passed": true }
  }
  ```
  `stored=false` with `quality_report.passed=false` means the gate rejected the data and
  nothing was written to the repo (the report itself still is).

**DI**: `get_data_adapter` + `get_repository` (both swappable via `app.dependency_overrides`).

---

## POST /api/v1/backtest
Run a **single** strategy backtest against a (symbol, config, range); returns the equity
curve and the metrics from `BacktestMetrics`. Intended for "what does this one config do?"
iteration — fast feedback before paying for the full /validate suite.

**Why sync**: plain `def`, threadpooled; yfinance + DB blocking work doesn't stall the loop.

**Cache-aside read path**: same as /validate. Repo first; on miss runs the ingestion pipeline,
then re-reads. Same `MIN_BARS=30` backstop.

**Request** (`BacktestRequest`):
```json
{
  "symbol": "AAPL",
  "strategy": { "name": "<catalog-name>", "...params": "..." },
  "start_date": "2024-01-01T00:00:00Z",
  "end_date":   "2024-12-01T00:00:00Z",
  "initial_capital": 100000.0,
  "cost_rate": 0.001
}
```
`strategy` is a Pydantic discriminated union (`Field(discriminator="name")`) over every
`STRATEGY_CATALOG` entry; see `GET /api/v1/strategies` for the full list and
per-strategy parameter schemas (ADR-010). Adding a strategy is a backend-only diff.

`initial_capital` (default `100_000.0`, `gt=0`) and `cost_rate` (default `0.001` = 10 bps
per unit turnover, `ge=0`) are optional engine overrides — let the caller sanity-check
what costs do to the equity curve (the most under-appreciated variable in retail
backtests). Both flow into `BacktestEngine(initial_capital=..., cost_rate=...)` and
are echoed back in the response.

An unknown `name`, a non-positive `initial_capital`, or a negative `cost_rate` is a
422 from Pydantic — never reaches the handler.

**Responses**:
- `200` → `BacktestResponse`:
  ```json
  {
    "symbol": "AAPL",
    "strategy_name": "sma_crossover",
    "parameters": { "fast": 5, "slow": 20 },
    "n_trades": 12,
    "cost_rate": 0.001,
    "metrics": {
      "sharpe": 1.5, "max_drawdown": -0.18, "total_return": 0.42,
      "annualized_return": 0.18, "annualized_vol": 0.12
    },
    "equity_curve": [{ "timestamp_utc": "...", "equity": 100000.0 }, "..."],
    "buy_and_hold_curve": [{ "timestamp_utc": "...", "equity": 100000.0 }, "..."],
    "buy_and_hold_total_return": 0.30,
    "drawdown_curve": [{ "timestamp_utc": "...", "drawdown": -0.05 }, "..."],
    "rolling_sharpe_curve": [{ "timestamp_utc": "...", "sharpe": 1.2 }, "..."],
    "rolling_sharpe_window": 60,
    "return_distribution": {
      "bins": [{ "bin_center": 0.0, "frequency": 80 }, "..."],
      "skewness": -0.42,
      "kurtosis": 1.85
    },
    "trade_markers": [
      { "timestamp_utc": "...", "direction": "buy", "equity": 101000.0 },
      { "timestamp_utc": "...", "direction": "sell", "equity": 103500.0 }
    ],
    "benchmark_comparison": {
      "benchmark_symbol": "SPY", "alpha": 0.037, "beta": 0.85,
      "information_ratio": 0.61, "tracking_error": 0.09,
      "benchmark_relative_drawdown": -0.12
    }
  }
  ```
  - `buy_and_hold_curve` is a 100% long position of the SAME symbol from t=0, same
    `initial_capital`, no costs — the canonical "is the strategy doing anything?" check.
  - `drawdown_curve` is `equity / cummax - 1` over the strategy curve; each `drawdown` is
    in `[-1, 0]` with `0` meaning "at peak".
  - `rolling_sharpe_curve` is the annualized rolling Sharpe of the strategy returns over
    `rolling_sharpe_window` bars (default 60); warmup values are `0.0` (not NaN).
  - `return_distribution` is the histogram of daily strategy returns plus sample
    `skewness` and **excess** `kurtosis` (Fisher convention — Gaussian == 0). Negative
    skew + high excess kurtosis = small wins / occasional large losses.
  - `trade_markers` are discrete position-direction changes (bars where
    `position.diff() != 0`). `direction` is `"buy"` when the change is positive (entering
    long, covering short, or flipping short -> long) and `"sell"` when it's negative; flat
    bars produce no markers. `equity` is the strategy's equity at that bar — used as the
    y-coordinate when overlaid on the equity-curve chart. The first bar with a non-zero
    position is NOT a marker (we mark signal *changes*, not the initial state). Empty list
    if the strategy never moves direction in the backtest window.
  - `benchmark_comparison` (ADR-013) is the strategy-vs-SPY decomposition: annualized
    `alpha`, `beta`, `information_ratio`, annualized `tracking_error`, and
    `benchmark_relative_drawdown` (worst underperformance vs SPY, in `[-1, 0]`). SPY is
    fetched via the same cache-aside path; when `symbol == "SPY"` the fetched series is
    reused. **The field is `null`** when the SPY series can't be fetched or doesn't overlap
    — a benchmark is context, not a precondition, so its absence never fails the backtest.
    The frontend Zod schema mirrors it as **nullable** ([[feedback-frontend-shadow-validators]]).
- `422` → insufficient data after the cache-miss ingest, or an unknown strategy discriminator.

**DI**: `get_data_adapter` + `get_repository`. Same overrides as /validate in tests.

---

## POST /api/v1/monte-carlo
Forward-looking risk of a strategy over a horizon (ADR-014 Phase 0). Runs the requested
strategy (cache-aside, same as /backtest), estimates the strategy's daily drift + vol from its
realized returns, and Monte-Carlo simulates `n_paths` GBM equity paths over `horizon_days`.

- **Request**: `{ symbol, strategy (StrategyConfig), start_date, end_date, horizon_days=252,
  n_paths=10000, loss_threshold=0.2, seed=42, initial_capital=100000, cost_rate=0.001 }`.
  `horizon_days >= 1`, `n_paths >= 1`, `loss_threshold ∈ (0, 1]` (else `422`).
- **Response** `MonteCarloResponse`:
  ```json
  {
    "symbol": "AAPL", "strategy_name": "sma_crossover", "parameters": {"fast": 5, "slow": 20},
    "horizon_days": 252, "n_paths": 10000, "loss_threshold": 0.2,
    "prob_terminal_loss": 0.12, "prob_max_drawdown_exceeds": 0.28,
    "terminal_return_p5": -0.18, "terminal_return_p50": 0.07, "terminal_return_p95": 0.41,
    "expected_terminal_return": 0.08
  }
  ```
  - `prob_terminal_loss` = P(strategy ends the horizon down more than `loss_threshold`).
  - `prob_max_drawdown_exceeds` = P(worst intra-horizon drawdown breaches `loss_threshold`);
    always `>= prob_terminal_loss` (an intra-horizon dip can recover by the end).
  - Terminal-return percentiles (`p5/p50/p95`) + `expected_terminal_return` describe the
    outcome distribution. **Deterministic under `seed`** — it flags POTENTIAL downside
    (rule 6), it does not predict. A risk gate for the StrategyLab, not a forecast.
- `422` → insufficient data (`< 30` bars) after the cache-miss ingest, or an unknown strategy.

**DI**: `get_data_adapter` + `get_repository`. Reuses `/backtest`'s `_load_frame` cache-aside.

---

## POST /api/v1/validate
Run the full validation suite for a strategy on a symbol; returns a `ValidationReport`.

**Why sync**: plain `def`, threadpooled by FastAPI — the blocking yfinance fetch and DB calls
do not stall the event loop (ADR-009).

**Cache-aside read path**: the handler reads bars from the injected `PriceBarRepository` first.
On miss (or insufficient cached bars) it runs `DataIngestionPipeline.ingest(...)` and re-reads
from the repo. Cache hits never call the data adapter.

**Request** (`ValidateRequest`):
```json
{
  "symbol": "AAPL",
  "strategy": "sma | momentum | mean_reversion",
  "start_date": "2020-01-01T00:00:00Z",
  "end_date":   "2024-01-01T00:00:00Z"
}
```
Given the resulting bars, the server builds the price frame, runs a built-in parameter grid
for the chosen strategy through `ValidationEngine`, and returns the report.

**Responses**:
- `200` → `ValidationReport`:
  ```json
  {
    "strategy_name": "sma",
    "observed_sharpe": 1.23,
    "deflated_sharpe": 0.41,
    "pbo": 0.18,
    "parameter_stability_score": 0.86,
    "n_walk_forward_splits": 5,
    "n_purged_folds": 5,
    "flags": [],
    "interpretations": [
      { "metric": "pbo", "message": "PBO 18% — overfitting risk is low.", "verdict": "good" },
      { "metric": "deflated_sharpe", "message": "...", "verdict": "good" },
      { "metric": "parameter_stability_score", "message": "...", "verdict": "good" }
    ],
    "passed": true
  }
  ```
  - `flags` are warning strings (e.g. "short sample" / "high PBO").
  - `interpretations` are backend-authored plain-English readings per metric, with a
    `verdict` of `good` / `warning` / `bad`. Thresholds: PBO ≥ 0.5 bad / 0.3–0.5 warning /
    < 0.3 good; DSR ≤ 0 bad / > 0 good; stability ≤ 0.4 bad / 0.4–0.7 warning / > 0.7 good.
- `422` → invalid `strategy` (not in the enum), or insufficient data (< 30 bars) even after
  the cache-miss ingest (e.g., the quality gate rejected the fetched bars).

**DI**: `get_data_adapter` + `get_repository` from `app.dependencies`; tests swap both via
`app.dependency_overrides` to feed synthetic fixtures and an `InMemoryPriceBarRepository`
(no network, no DB in CI).
