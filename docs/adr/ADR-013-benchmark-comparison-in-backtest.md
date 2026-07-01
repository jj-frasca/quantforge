# ADR-013: Surface benchmark comparison (alpha/beta/IR) in the BacktestResponse

- **Status**: Accepted
- **Date**: 2026-06-30
- **Deciders**: Joe Frasca

## Context
`backend/app/research/benchmarks/comparator.py` implements `BenchmarkComparator` —
aligning a strategy's daily returns against a benchmark (default SPY) and reporting
alpha, beta, information ratio, tracking error, and benchmark-relative drawdown. It is
fully implemented and unit-tested, but it is **dead code**: nothing calls it, and no
API surface exposes the numbers. The `/backtest` response reports absolute metrics
(Sharpe, max drawdown, total return) plus a same-symbol buy-and-hold overlay, but never
answers the question every quant interview opens with: *did you actually beat the market?*

Absolute Sharpe is not the whole story. A 0.9 Sharpe that is 95% beta to SPY is not an
edge — it is leverage on the index. Alpha/beta/IR are the standard academic decomposition
that separates skill from market exposure, and the module to compute them already exists.

Two questions to settle: (1) where the comparison belongs (new endpoint vs. extension of
`/backtest`), and (2) how to handle the benchmark data fetch and its failure modes.

## Options Considered

1. **New `POST /api/v1/benchmark-comparison` endpoint**, called separately by the frontend.
   - Pro: cleanly factored; a benchmark comparison is conceptually distinct from a backtest.
   - Con: forces two requests for one user action ("Run backtest"), duplicates the
     data-fetch + strategy-run path (the comparison needs the strategy's *returns*, which
     only the backtest produces), and introduces a timing skew where the equity curve
     renders before the alpha/beta lands. Same rejection as ADR-012 option 1.

2. **Extend the `/backtest` response** with an optional `benchmark_comparison` field. The
   route fetches SPY over the same window (same cache-aside pipeline), computes SPY
   buy-and-hold returns, runs `BenchmarkComparator().compare(strategy_returns, spy_returns)`,
   and serializes the scalars. The frontend renders them below the equity curve.
   - Pro: one request, one response, one piece of UI. The route already has the strategy
     returns in hand (`result.returns`). Mirrors the ADR-012 shape exactly.
   - Con: the route now does a second (cache-aside) data fetch; the response schema grows;
     a benchmark-fetch failure must not take down the core backtest.

3. **Serialize the full excess-returns series** (per-bar strategy-minus-benchmark) for an
   excess-return chart, in addition to the scalars.
   - Pro: richer — an excess-return curve shows *when* the alpha accrued.
   - Con: doubles the payload for a chart nobody has asked for yet. The scalars answer the
     load-bearing question; the equity curve already shows relative shape against B&H.
     Premature — add later if wanted (open to a follow-on ADR).

## Decision

Take **option 2, scalars only**. Extend `BacktestResponse` with:

```
benchmark_comparison: BenchmarkComparisonView | None
```

where `BenchmarkComparisonView = {benchmark_symbol: str, alpha: float, beta: float,
information_ratio: float, tracking_error: float, benchmark_relative_drawdown: float}`.

Mechanics:
- Benchmark is **SPY**, hardcoded (matches `BenchmarkComparator`'s default; not a form knob
  in the MVP — exposing it adds noise for negligible gain, same call as ADR-012's window).
- The route fetches SPY via the **same cache-aside pipeline** used for the requested symbol,
  computes SPY buy-and-hold daily returns (`spy_close.pct_change()`), and calls
  `compare(result.returns, spy_returns)`. `compare` already inner-joins on the index.
- **When `symbol == "SPY"`**, reuse the symbol's own close series for the benchmark returns
  instead of a redundant second fetch. This is still a meaningful comparison (a strategy on
  SPY vs. holding SPY); only a buy-and-hold-vs-buy-and-hold run is the degenerate oracle.
- **`benchmark_comparison` is nullable**: if the SPY fetch fails or yields insufficient
  overlapping bars, the field is `None` and the core backtest still returns 200. A benchmark
  is context, not a precondition — a data-vendor hiccup on SPY must not deny the user their
  strategy's own equity curve. The frontend renders the section only when the field is present.

## Consequences

What becomes easier:
- Every `/backtest` now answers "did you beat SPY, and how much of your return is just beta?"
  — the single highest-signal thing a recruiting reviewer looks for. `BenchmarkComparator` is
  no longer dead code.
- One user action returns one self-contained result, consistent with the existing pattern.

What becomes harder / new obligations:
- The `/backtest` Pydantic schema grows; the matching frontend **Zod** schema must add
  `benchmark_comparison` as **nullable** — a mirrored non-nullable field would 422 legitimate
  benchmark-less responses ([[feedback-frontend-shadow-validators]]).
- The route now issues a second cache-aside fetch on a cold store. Warm-cache SPY is cheap;
  the first cold run pays one extra yfinance fetch. Acceptable — SPY is the most-cached symbol
  in any run and the fetch is skipped entirely when `symbol == "SPY"`.
- `api-contracts.md` and `ARCHITECTURE.md` §0.6 must document the new field in lockstep
  ([[feedback-code-docs-paired-artifacts]]).

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*
