# API Contracts (Cold Memory)

FastAPI endpoint specifications. Read when working on `backend/app/api/`. Endpoints are
versioned under `/api/v1`. Response bodies are Pydantic models (auto-documented at `/docs`).

Phase 5 will expand this (data explorer, strategy config, backtest results). The validation
endpoint below ships first because the ValidationReport is the MVP deliverable.

---

## GET /health
Liveness probe. → `200 {"status": "ok", "environment": "<env>"}`. No DB dependency.

---

## POST /api/v1/validate
Run the full validation suite for a strategy on a symbol; returns a `ValidationReport`.

**Why sync**: the handler is a plain `def`, so FastAPI runs it in a threadpool — the blocking
yfinance fetch does not stall the event loop (provisional pending ADR-009; see ADR-009).

**Request** (`ValidateRequest`):
```json
{
  "symbol": "AAPL",
  "strategy": "sma | momentum | mean_reversion",
  "start_date": "2020-01-01T00:00:00Z",
  "end_date":   "2024-01-01T00:00:00Z"
}
```
The server fetches bars via the injected `DataSourceAdapter` (yfinance in prod; overridden in
tests), builds the price frame, runs a built-in parameter grid for the chosen strategy through
the `ValidationEngine`, and returns the report.

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
- `422` → invalid `strategy` (not in the enum), or insufficient data (< 30 bars).

**Dependency injection**: the data adapter is provided by `app.dependencies.get_data_adapter`;
tests swap it via `app.dependency_overrides` to feed synthetic fixtures (no network in CI).
