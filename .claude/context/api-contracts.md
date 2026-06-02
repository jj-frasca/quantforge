# API Contracts (Cold Memory)

FastAPI endpoint specifications. Read when working on `backend/app/api/`. Endpoints are
versioned under `/api/v1`. Response bodies are Pydantic models (auto-documented at `/docs`).

Phase 5 will expand this (data explorer, strategy config, backtest results). The validation
endpoint below ships first because the ValidationReport is the MVP deliverable.

---

## GET /health
Liveness probe. → `200 {"status": "ok", "environment": "<env>"}`. No DB dependency.

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
  "strategy": { "name": "sma" | "momentum" | "mean_reversion", "...params": "..." },
  "start_date": "2024-01-01T00:00:00Z",
  "end_date":   "2024-12-01T00:00:00Z"
}
```
`strategy` is a Pydantic discriminated union (`Field(discriminator="name")`):
- `sma`: `{ name: "sma", fast: int, slow: int }`
- `momentum`: `{ name: "momentum", lookback: int, skip: int }`
- `mean_reversion`: `{ name: "mean_reversion", window: int, k: float }`

An unknown `name` is a 422 from Pydantic — never reaches the handler.

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
    "equity_curve": [{ "timestamp_utc": "...", "equity": 100000.0 }, "..."]
  }
  ```
- `422` → insufficient data after the cache-miss ingest, or an unknown strategy discriminator.

**DI**: `get_data_adapter` + `get_repository`. Same overrides as /validate in tests.

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
    "passed": true
  }
  ```
- `422` → invalid `strategy` (not in the enum), or insufficient data (< 30 bars) even after
  the cache-miss ingest (e.g., the quality gate rejected the fetched bars).

**DI**: `get_data_adapter` + `get_repository` from `app.dependencies`; tests swap both via
`app.dependency_overrides` to feed synthetic fixtures and an `InMemoryPriceBarRepository`
(no network, no DB in CI).
