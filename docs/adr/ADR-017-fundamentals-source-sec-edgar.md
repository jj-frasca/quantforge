# ADR-017: Fundamentals data layer via SEC EDGAR (sentiment deferred)

- **Status**: Accepted
- **Date**: 2026-07-01
- **Deciders**: Joe Frasca
- **Implements**: ADR-014 (harness — fundamentals as filter + features)

## Context
The StrategyLab needs a fundamentals layer — P/E, revenue growth, margins — as both a universe
*filter* ("only trade names with sane fundamentals") and as *features*, and Joe requires every
figure to be **citation-backed and refreshed often**. Vendor research (2026-07-01) compared SEC
EDGAR, Financial Modeling Prep, Alpha Vantage, and Finnhub on cost, coverage, and
citation-quality.

## Decision

### Fundamentals source = SEC EDGAR CompanyFacts
`https://data.sec.gov/api/xbrl/companyfacts/CIK{10-digit}.json` — the official XBRL facts from
every filing. Chosen because:
- **Citation-native**: each datum cites a real filing (form, accession number, fiscal period,
  filed date, URL). This IS the primary source; paid APIs resell it. Directly satisfies the
  "backed with citations" requirement ([[feedback-code-docs-paired-artifacts]] ethos for data).
- **$0, no API key, 30+ years**, ~10 req/s (needs a descriptive `User-Agent`).
- Fits the existing adapter pattern: a `FundamentalsSource` parallel to `DataSourceAdapter`.

Access via direct `requests`/`httpx` + a focused parser (no heavy dependency); the parser tries
an ordered list of candidate GAAP tags per concept (e.g. `RevenueFromContractWithCustomer
ExcludingAssessedTax` → `Revenues` → `SalesRevenueNet`) because tag usage varies by filer.
[ASSUMPTION: those tag fallbacks cover the large-cap universe; verified against fixtures + a
live smoke test as we add symbols.]

### Contract — `FundamentalSnapshot`
Point-in-time, citation-carrying, JSON-round-tripping:
```
symbol, cik, as_of (filed date), fiscal_period (e.g. "FY2024"/"Q3-2024"), form ("10-K"/"10-Q"),
accession_number, source_url,
revenue_ttm, revenue_growth_yoy, gross_margin, net_margin, eps_ttm,
pe_ratio | None   # None until joined with a price from the yfinance layer
```
`source` is always `"SEC EDGAR"`. Copy follows rule 6 — "reported by the filer", never a claim
of correctness.

### Freshness
Fundamentals move on filings, not ticks — a **TTL cache** (default ~7 days) keyed by symbol; a
refresh re-pulls CompanyFacts and picks up any new filing. This matches the long-term-strategy
mandate (ADR-015) and the ~10 req/s limit.

### Testing (mirrors the yfinance adapter split)
- **Unit (CI)**: parse a checked-in CompanyFacts JSON fixture → deterministic `FundamentalSnapshot`;
  test the tag-fallback logic and missing-concept handling. No network.
- **Live (`@pytest.mark.live`, not in CI)**: a real EDGAR pull for one symbol, run locally.

### Sentiment — DEFERRED to a follow-on ADR
Free sentiment tiers are stingy/inconsistent and it's a distinct NLP concern (news + model,
citation = article URLs). Ship fundamentals first; add sentiment as its own slice (likely news
headlines + a local FinBERT/VADER, cited per article, or a vendor if a free tier proves adequate).

## Options Considered
- **FMP / Alpha Vantage / Finnhub.** Rejected as the primary: they resell EDGAR (weaker citation
  provenance), gate history/coverage behind stingy free tiers, and add a paid dependency for data
  we can get authoritatively for free. Revisit only if EDGAR parsing coverage proves inadequate.
- **Bundle sentiment now.** Rejected: delays the clean, high-value fundamentals work for a noisier
  layer with poor free-tier economics.
- **Add `edgartools` dependency.** Deferred: a focused parser for the handful of concepts we need
  keeps the dependency surface small; adopt `edgartools` if parsing breadth demands it.

## Consequences
- Fundamentals become a $0, fully-cited layer the search can filter/feature on; graduates can
  carry "traded only names with positive revenue growth + healthy margins, per their 10-K".
- New obligations: XBRL tag-fallback maintenance as we widen the universe; a TTL cache; P/E needs
  a price join with the existing data layer.
- Sentiment remains unbuilt until its own ADR.

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*
