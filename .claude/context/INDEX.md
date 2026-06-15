# Cold Memory Index (Tier 3)

Master index of the on-demand specification docs. These are NEVER auto-loaded —
an agent reads the relevant one explicitly when a task calls for it. Each doc is
self-contained: it gives everything needed for its subsystem.

| Doc | Covers | Status |
|---|---|---|
| `data-contracts.md` | PriceBar/FundamentalData/DataQualityReport schemas, SQL patterns, mandatory TimescaleDB query filters | **Written** (Phase 2) |
| `backtesting-spec.md` | BacktestEngine (position/cost/equity math — no separate Portfolio class), Metrics, BenchmarkComparator, ExperimentManifest | **Written** (Phase 3) |
| `validation-methodology.md` | PBO, purged CV, walk-forward, Deflated Sharpe, parameter stability, regime analysis | **Written** (Phase 4) |
| `research-papers.md` | Citations with implementation summaries (Bailey et al. 2015, López de Prado 2018, etc.) | **Written** (Phase 3) |
| `api-contracts.md` | Full FastAPI endpoint specifications, response schemas, versioning | **Written** (Phase 5) — all 6 endpoints documented (/health, /strategies, /ingest, /bars, /backtest, /validate) |

## Rule
Per ARCHITECTURE.md §2.3: data contracts are written BEFORE the schema they describe.
Cold-memory docs hold formal schemas/SQL, paper summaries, full API contracts, and
mathematical definitions — NOT behavioral rules (those live in CLAUDE.md) and NOT
domain heuristics (those live in agent specs). See ARCHITECTURE.md §6.0.
