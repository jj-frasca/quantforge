# ADR-029: Fundamental-research division (quality scoring + its own discovery + quantamental combination)

- **Status**: Accepted
- **Date**: 2026-08-18
- **Deciders**: Joe Frasca
- **Extends**: ADR-017 (fundamentals veto), ADR-022 (valuation/UndervaluationScore), ADR-023 (value gate),
  ADR-024 (cross-sectional), ADR-026 (sharded discovery)

## Context
Joe wants a standing "division" that does regular, institutional-grade fundamental research on public
companies — the way a quantamental fund does — so we have a clear view of which companies are genuinely
*good businesses*, and can combine that with the advanced trading strategies. It should have its OWN
discovery loop that eventually gets through every public company, and it must combine with the technical
engine (Joe left the exact combination to us).

External research (2025–26) is consistent: the durable edge is **quantamental** — quantitative signals
plus fundamental judgment — and the fundamental side is best captured by a handful of well-cited,
computable **quality** factors layered on top of the **value** work we already have (ADR-022):
- **Piotroski F-Score** (9 binary points: profitability, leverage/liquidity, operating efficiency) —
  +7.5%/yr on value stocks (Piotroski 2000).
- **Novy-Marx gross profitability** (gross profit / total assets) — "the other side of value" (2013).
- **Altman Z-Score** (bankruptcy/distress risk) — a safety screen.
- **Quality-Minus-Junk** spirit (Asness, Frazzini, Pedersen 2019): profitability + growth + safety.

We already have: `valuation/` (FCFE DCF, multiples, `UndervaluationScore`), `SecEdgarFundamentalsSource`
(income-statement facts + history), the ADR-017 fundamentals veto, and the ADR-023 value provider. What
we LACK is (a) the balance-sheet + cash-flow line items the quality factors need, (b) a quality engine,
(c) a dedicated fundamental discovery sweep, and (d) explicit combination with the strategy engine.

## Decision
Build a **`fundamentals/` research division** in four layers, each judged for honesty the same way the
rest of the platform is (cite the filing; flag potential, never guarantee — CLAUDE.md rule 6).

### 1. Extend the EDGAR data (data-engineering)
Add the missing line items to `SecEdgarFundamentalsSource` + the `AnnualFundamentals`/`FundamentalsHistory`
models (all standard US-GAAP tags): total assets, total current assets, total current liabilities,
long-term debt, gross profit (or COGS to derive it), operating cash flow, retained earnings, total
equity. Additive only — do not break the existing income-statement fields or the ADR-022/023 consumers.

### 2. Fundamental quality engine (`app/research/fundamentals/`)
Pure, cited scoring functions over `FundamentalsHistory` (no network; injectable in tests):
- `piotroski_f_score(history) -> FScore` (0–9, with the 9 component booleans exposed for legibility).
- `gross_profitability(history) -> float` (Novy-Marx: gross profit / total assets).
- `altman_z_score(history) -> float` (distress; report the zone).
- `quality_score(history) -> QualityScore` — a frozen, cited composite in [0,1] blending the above
  (rank/percentile-normalized where scales differ), with the components + flags surfaced.
This COMPLEMENTS `UndervaluationScore` (value): quality = "is it a good business?", value = "is it cheap?".

### 3. Fundamental discovery — sweep every public company
A dedicated, token-free discovery loop (EDGAR is free, no LLM):
- Enumerate the CIK universe from SEC's `company_tickers.json`; shard it (ADR-026 pattern) so a matrix
  of jobs works through the full list of public filers over time and then revisits (fundamentals update
  quarterly, so a slow full sweep + revisit cadence is right).
- Each shard fetches history, computes `quality_score` + `UndervaluationScore`, and writes a
  `FundamentalRecord` (symbol, cik, quality, value, components, as-of filing) to a sharded output.
- A consolidation job merges into `data/fundamentals_pool.json` (dedup by cik, keep latest as-of),
  BOUNDED like the research pool (ADR-026 prune fix — cap size). A leaderboard ranks companies by a
  combined quality+value score: the "genuinely good, reasonably priced companies" list.

### 4. Quantamental combination — layered complements (all three, not either/or)
Joe asked whether fundamentals gate strategies, seed strategies, or stand alone. **All three**, because
they attack different points and compose cleanly:
- **(a) Standalone cross-sectional factor** `xs_quality` (and `xs_quality_value`): rank the universe by
  `quality_score` (and quality×value), long the top / short the bottom — a fundamental factor judged by
  the SAME DSR/PBO/holdout gate as every technical factor (ADR-024). Fundamentals earn their place, not
  assumed. (Point-in-time caveat carried from ADR-024: as-of snapshot, not full PIT history yet.)
- **(b) Universe pre-filter for the technical hunt**: an opt-in mode where the single-name / cross-
  sectional hunt runs only on the top-quality-value companies — a better hunting ground (fewer junk
  names), honest because it just narrows WHERE we search, not the gate.
- **(c) Extended graduation context**: surface each graduate's quality+value alongside its DSR on the
  leaderboard/dashboard, and extend the ADR-017 veto so a name failing a hard *distress* screen (e.g.
  Altman Z in the distress zone) cannot graduate regardless of technicals — a business-quality safety
  rail on top of the statistical one.

### Honesty
Fundamentals do not weaken the gate. As a factor they clear the same DSR/PBO/holdout bar; as a filter
they only narrow the universe; as a veto they only ADD a distress safety rail. Every score cites its
filing and flags potential, never guarantees (rule 6). The full sweep is more breadth, same rigor.

## Options Considered
- **Only a value screen (what we have).** Rejected — value alone buys cheap junk; quality is the missing
  half of "good companies," and the research is emphatic that quality+value together is the edge.
- **One combination mode only.** Rejected — factor vs. filter vs. veto serve different purposes and
  compose; committing to one throws away the others for no benefit.
- **Buy a fundamentals data vendor.** Rejected for now — SEC EDGAR is free, complete for US filers, and
  already integrated; a vendor is a later option if coverage/PIT history demands it.

## Consequences
- A genuine second research engine: a growing, ranked view of the fundamental quality of every US public
  company, updated on a sweep+revisit cadence, feeding the trading engine three ways.
- New obligations: extend EDGAR (more tags → more parsing fragility; guard per-field like the rest),
  bound the fundamentals pool (ADR-026 prune), and PIT-history rigor is deferred (as-of snapshots first,
  point-in-time fundamentals a later ADR — the honest caveat travels with `xs_quality`).
- This is built by a TEAM: the planner architects (this ADR) and reviews; executors implement the layers.

## References
- Piotroski (2000), "Value Investing: The Use of Historical Financial Statement Information."
- Novy-Marx (2013), "The Other Side of Value: The Gross Profitability Premium": https://mysimon.rochester.edu/novy-marx/research/QDoVI.pdf
- Asness, Frazzini, Pedersen (2019), "Quality Minus Junk."
- Altman (1968), Z-Score. Quantamental overview: https://midscapital.medium.com/quantamental-investing-merging-quantitative-and-fundamental-analysis-c7656eeecf41
- Robeco (2025), "Seizing quant and fundamental alpha": https://www.robeco.com/files/docm/docu-20250624-seizing-quant-and-fundamental-alpha-in-developed-equity-markets-hksg.pdf

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*
