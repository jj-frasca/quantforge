# ADR-022: Value research engine — undervaluation scoring from EDGAR fundamentals

- **Status**: Accepted
- **Date**: 2026-07-08
- **Deciders**: Joe Frasca
- **Implements**: mission north star (DELEGATION.md WP-C) — combine the algo strategies with a
  value engine that identifies *genuinely undervalued* companies.

## Context
The lab hunts technical edges; Joe wants to pair it with a **value research engine** that scores
how *undervalued* a company is, so the universe can be filtered/ranked on cheapness as well as
price action. We already have a citation-backed fundamentals layer (ADR-017: SEC EDGAR
CompanyFacts → `FundamentalSnapshot`), but it returns only the **latest** fiscal year. Valuation
needs two things that snapshot can't give: a **history** of line items (to judge a multiple
against the company's own past) and a way to turn cash flows into an **absolute** value.

Three forces shape the decision:
1. **Peers are hard and noisy.** A defensible peer set (GICS sub-industry, size, capital
   structure) is a research project of its own and easy to get wrong. Rule 6 forbids overclaiming.
2. **Multiples-vs-history need prices EDGAR doesn't have.** P/E and P/S over time require joining
   each fiscal year's EDGAR figures with a market price near that year end.
3. **Absolute value is assumption-driven.** A DCF is only as honest as its disclosed assumptions;
   it must record them and flag every fallback, never present a single confident "fair value".

## Options Considered
1. **Peer-relative multiples first (P/E vs sector median).**
   - Pro: the most intuitive "cheap vs its rivals" framing.
   - Con: requires a defensible peer set + peer fundamentals for each name; high effort, easy to
     mislead; contradicts the WP-C guidance ("peers are hard — self-history + absolute first").
2. **Self-history multiples + absolute DCF first (chosen).**
   - Pro: every input is the company's own citation-backed filings + its own price; no peer
     modelling; directly satisfies "undervalued vs its own past" and "vs intrinsic value".
   - Con: self-history says nothing about whether the *whole sector* is cheap; DCF carries
     assumption risk. Both mitigated by disclosing assumptions + flagging thin history.
3. **Full DCF with net-debt bridge + EV/EBITDA now.**
   - Pro: more complete enterprise valuation.
   - Con: needs debt/cash/EBITDA balance-sheet tags (a fundamentals-history expansion) and a
     net-debt bridge — more surface area, more tag-fallback maintenance, more ways to be wrong on
     day one. Defer to a follow-on once the honest core proves useful.

## Decision
Build `backend/app/research/valuation/` on top of a **fundamentals *history*** extracted from the
same EDGAR CompanyFacts payload. Scope slice 1 to two peer-free, citation-backed signals plus a
composite, all honest per rule 6:

- **Fundamentals history** (in `app/data/fundamentals.py`, additive — `fetch`/`parse_company_facts`
  untouched): `AnnualFundamentals` (fiscal_year, revenue, net_income, eps, shares_diluted,
  free_cash_flow, and an optional `price` joined *upstream* from the price layer — EDGAR has no
  prices) + `FundamentalsHistory` (cited: cik/form/accession/url) + `parse_company_facts_history`.
  `SecEdgarFundamentalsSource.fetch_history` is the live pull (new method, existing `fetch` intact).
- **Multiples vs own history** (`multiples.py`): P/E and P/S. The *current* multiple (current price
  ÷ latest EPS; current price × latest shares ÷ latest revenue) is percentile-ranked within the
  company's **own** historical distribution (each year's price ÷ that year's figure). A low
  percentile flags "cheap vs its own past". `EV/EBITDA is DEFERRED` (needs debt/cash/EBITDA tags).
- **Absolute intrinsic value** (`intrinsic_value.py`): a simple **FCFE DCF** — project base free
  cash flow (net income used as a flagged proxy when FCF is unavailable) at a clamped, history-
  derived growth for N years, Gordon terminal value, discount at cost of equity, ÷ diluted shares.
  All knobs live in a tunable frozen `DcfAssumptions` (discount_rate 10%, terminal_growth 2.5%,
  projection_years 5, growth clamp) with `discount_rate > terminal_growth` enforced. Margin of
  safety = (intrinsic − price) / intrinsic. Simplification: discounts equity FCF directly, so it
  ignores a separate net-debt bridge — disclosed here, not hidden.
- **Composite** (`score.py`): `UndervaluationScore` (frozen, cited to the latest 10-K) carrying the
  current multiples, their own-history percentiles, the DCF value, margin of safety, and a 0–1
  heuristic `score` = mean of the *available* components `(1−pe_pct, 1−ps_pct, clamp(MoS,0,1))`.
  Missing inputs never silently default — each becomes a `flag`. `score` is None when nothing is
  computable. Copy says "flags potentially undervalued", never "is undervalued".

## Consequences
- The universe gains a $0, fully-cited **value axis** to filter/rank on, independent of WP-A/B/D.
- New obligations: the price-per-fiscal-year **join** lives upstream of this module (the module
  consumes `AnnualFundamentals.price`); years without a price are skipped from percentiles and
  flagged. The DCF's honesty rests on disclosing its assumptions on every result.
- Deferred (own follow-on): **peer-relative** multiples, **EV/EBITDA** + a **net-debt bridge**
  (needs debt/cash/EBITDA history), and using valuation **as a live signal/veto** inside
  `run_search` (this ADR ships the scorer; wiring it into the hunt is a separate slice).
- More XBRL tag-fallback maintenance (shares/OCF/capex tags now, in addition to ADR-017's set).

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*
