# QuantForge — C4 Architecture Diagrams

C4 model (Context → Container) plus the canonical data-flow pipeline. Rendered by any
Mermaid-aware viewer (GitHub, VS Code Mermaid extension).

## Level 1 — System Context

Who uses QuantForge and what it depends on.

```mermaid
C4Context
    title System Context — QuantForge
    Person(researcher, "Quant Researcher", "Configures strategies, runs backtests, reads validation reports")
    System(quantforge, "QuantForge", "AI-native quant research & validation platform")
    System_Ext(yfinance, "yfinance", "Free OHLCV market data — PRIMARY source (no API key)")
    System_Ext(polygon, "Polygon.io", "Market data — second vendor (Phase 3+, optional)")
    System_Ext(alpaca, "Alpaca (paper account)", "Paper-only forward-test execution — no real money (ADR-019/020/021)")
    Rel(researcher, quantforge, "Configures & reviews results", "HTTPS")
    Rel(quantforge, yfinance, "Fetches OHLCV via DataSourceAdapter", "HTTPS")
    Rel(quantforge, polygon, "Fetches OHLCV via DataSourceAdapter", "HTTPS")
    Rel(quantforge, alpaca, "Places/reconciles paper orders", "HTTPS")
    UpdateRelStyle(quantforge, polygon, $lineColor="grey")
```

## Level 2 — Containers

The deployable/runtime pieces.

```mermaid
C4Container
    title Container Diagram — QuantForge
    Person(researcher, "Quant Researcher")
    System_Boundary(qf, "QuantForge") {
        Container(spa, "Frontend SPA", "React 19 + TypeScript, Vite", "Data Explorer, Strategy Config, Backtest Results, Validation Report, Compare Configs, About")
        Container(api, "Backend API", "Python 3.12, FastAPI", "Data layer, research engine, validation engine, execution layer")
        ContainerDb(tsdb, "TimescaleDB", "PostgreSQL + hypertables", "OHLCV, fundamentals, quality reports, experiment lineage")
        ContainerDb(redis, "Redis", "redis", "Low-latency price cache")
    }
    System_Ext(vendors, "yfinance / Polygon", "Market data vendors")
    System_Ext(alpaca, "Alpaca (paper account)", "Paper-only execution, no real money")
    Rel(researcher, spa, "Uses", "HTTPS")
    Rel(spa, api, "Calls", "JSON / HTTPS /api/v1")
    Rel(api, tsdb, "Reads & writes", "SQLAlchemy 2.0 sync / psycopg3 (ADR-009)")
    Rel(api, redis, "Caches prices", "redis-py")
    Rel(api, vendors, "Ingests (normalize at ingestion)", "HTTPS")
    Rel(api, alpaca, "Sizes, places, and idempotently reconciles paper orders", "HTTPS")
```

## Canonical Data Flow

The invariant pipeline (CLAUDE.md): every datum crosses the quality gate before any
research or validation component can use it.

```mermaid
flowchart LR
    src["DataSourceAdapter<br/>(yfinance / polygon)"] --> norm["Normalizer<br/>(UTC, Decimal, adj_factor×1)"]
    norm --> q{"DataQualityEngine<br/>passed?"}
    q -- "no" --> rej["Flag potential issues<br/>(not used downstream)"]
    q -- "yes" --> store[("TimescaleDB")]
    store --> strat["Strategy.generate_signals<br/>(signals ∈ [-1, 1])"]
    strat --> bt["BacktestEngine + Portfolio<br/>(transaction costs applied)"]
    bt --> bench["BenchmarkComparator<br/>(vs SPY)"]
    bench --> val["Validation<br/>PBO · purged CV · walk-forward · DSR"]
    val --> report["ValidationReport"]
    bt -.records.-> manifest["ExperimentManifest<br/>(reproducibility lineage)"]
```

## Component layering (within the Backend API)

```mermaid
flowchart TB
    subgraph data["app/data/ — Data Engineering (Phase 2)"]
        sources --> normalizers --> quality --> storage
    end
    subgraph research["app/research/ — Research Engine (Phase 3)"]
        strategies --> backtesting
        simulation
        benchmarks
    end
    subgraph validation["app/validation/ — Validation Engine (Phase 4)"]
        pbo & purged_cv & walk_forward & deflated_sharpe & regime --> reportmod["report.py"]
    end
    subgraph execution["app/execution/ — Paper Execution (ADR-019/020/021)"]
        sizing --> alpaca_broker["alpaca_broker.py"] --> equity_curve
    end
    data --> research --> validation
    validation --> execution
    api["app/api/v1 — FastAPI"] --> research
    api --> data
    api --> validation
    api --> execution
```
