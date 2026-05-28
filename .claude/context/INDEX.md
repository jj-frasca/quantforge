# Cold Memory Index (Tier 3)

Master index of the on-demand specification docs. These are NEVER auto-loaded —
an agent reads the relevant one explicitly when a task calls for it. Each doc is
self-contained: it gives everything needed for its subsystem.

| Doc | Covers | Status |
|---|---|---|
| `data-contracts.md` | PriceBar/FundamentalData/DataQualityReport schemas, SQL patterns, mandatory TimescaleDB query filters | Not yet written — authored at the start of **Phase 2** (before the schemas it describes) |
| `backtesting-spec.md` | BacktestEngine, Portfolio, Metrics, BenchmarkComparator, ExperimentManifest | Not yet written — authored at the start of **Phase 3** |
| `validation-methodology.md` | PBO, purged CV, walk-forward, Deflated Sharpe, parameter stability, regime analysis | Not yet written — authored at the start of **Phase 4** |
| `research-papers.md` | Citations with implementation summaries (Bailey et al. 2015, López de Prado 2018, etc.) | Not yet written — authored alongside Phase 3/4 |
| `api-contracts.md` | Full FastAPI endpoint specifications, response schemas, versioning | Not yet written — authored at the start of **Phase 5** |

## Rule
Per ARCHITECTURE.md §2.3: data contracts are written BEFORE the schema they describe.
Cold-memory docs hold formal schemas/SQL, paper summaries, full API contracts, and
mathematical definitions — NOT behavioral rules (those live in CLAUDE.md) and NOT
domain heuristics (those live in agent specs). See ARCHITECTURE.md §6.0.
