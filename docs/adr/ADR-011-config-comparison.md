# ADR-011: Compare-configs page via N parallel /backtest calls

- **Status**: Accepted
- **Date**: 2026-06-19
- **Deciders**: Joe Frasca

## Context
The standing feature shortlist after the "democratize advanced trading" UX track
has a Compare-configs page at the top of the remaining-product-feature column. ADR-010
§Consequences already foreshadowed it: *"the next product feature is a 'compare configs'
page that overlays N backtests of different param sets."*

A research platform whose smallest unit of comparison is one backtest at a time looks
like a backtest app, not a research platform. The whole point of PBO and CSCV (ADR-008,
[research-papers.md]) is that **the worst-case-over-many-configs is the only honest read**.
Surfacing that intuition in the UI — N equity curves overlaid on the same chart, with a
table of metrics per row — is the most direct way to make the methodology visible to
someone who hasn't read the papers.

The question this ADR settles is the **back-end shape**: should this be a new endpoint
(`POST /api/v1/compare`) that takes a list of configs and returns a list of results, or
should the frontend just fire N parallel `POST /api/v1/backtest` calls?

Constraints already fixed:
- DB access is sync `def` (ADR-009); FastAPI threadpools sync routes.
- All current endpoints are versioned at `/api/v1` (api-contracts.md).
- Frontend uses Tanstack Query (rules/frontend-typescript.md); parallel mutations are
  trivial via `Promise.all(mutations.map(m => m.mutateAsync(...)))`.
- N ∈ [2, 6] is the useful range — 1 is just a backtest, >6 makes the chart unreadable.

## Options Considered

1. **New `POST /api/v1/compare` endpoint** — accepts `{ symbol, dates, capital, cost, configs[] }`,
   returns `{ results: BacktestResponse[] }`.
   - Pro: one wire round-trip; the backend can parallelize internally (asyncio.gather or a
     ThreadPoolExecutor), bypassing any browser per-origin connection cap; the request
     payload is naturally batched.
   - Con: a whole new endpoint contract (request schema, response schema, OpenAPI doc,
     error semantics — does a single-config failure fail the whole batch?). Duplicates
     /backtest's per-config validation. Adds a backend surface that exists only to
     paper-over a thing the frontend can already do.

2. **N parallel `POST /api/v1/backtest` calls from the frontend** — one Tanstack Query
   `useMutation` per config, fired together via `Promise.all`.
   - Pro: zero new backend surface; reuses the existing /backtest contract verbatim;
     per-config errors land in per-config alert slots automatically (one failure doesn't
     poison the others); the FastAPI threadpool already concurrent-runs sync routes.
   - Con: N HTTP round-trips. For local dev that's negligible (~100 ms each); for a
     deployed config with significant network latency it could add 200–500 ms wall-clock
     vs. a single batched call. With N ≤ 6 still well inside acceptable UX (<2 s end-to-end).

3. **Sequential `POST /api/v1/backtest` calls in a single mutation** — fire one, await,
   fire next, repeat.
   - Pro: dead simple; deterministic completion order; per-row error handling.
   - Con: N× the wall-clock of the parallel option; defeats the user's expectation that
     "Run comparison" is one action.

## Decision

Take option 2: **N parallel `POST /api/v1/backtest` calls from the frontend.** The page
will accept a single (symbol, strategy, dates, capital, cost) and N param-row overrides
(2 ≤ N ≤ 6), construct N distinct `BacktestRequest` bodies, and fire them via a single
custom hook (`useCompareBacktests`) that wraps `Promise.allSettled` around the existing
`/backtest` mutation. Errors are per-row; one config failing does not poison the others.

The chart overlays the N equity curves on a single Recharts ComposedChart, color-coded
per config row. Below the chart, a small table shows each row's params + the canonical
metrics (Sharpe, annualized return, annualized vol, max DD, total return, # trades).

This keeps the backend's surface unchanged and lets the page be built and shipped without
any new server-side decision to make.

## Consequences

What becomes easier:
- No new backend endpoint to design, version, test, or document. The /backtest contract
  remains the single source of truth for one-config semantics.
- Per-row error handling is automatic — each Tanstack Query mutation owns its own error
  slot, so a single bad config doesn't blank the rest.
- The page can be deleted or rewritten without coordinating with backend.

What becomes harder / new obligations:
- The frontend now owns "fan-out N requests" as a concept. The `useCompareBacktests`
  hook is the only place this lives — must not leak that fan-out into components.
- If a future deployment surfaces network latency that makes N round-trips visibly slow,
  the answer is a future ADR that adds a `POST /api/v1/compare` endpoint as a strict
  performance optimization (not a feature add). The frontend must be structured so that
  flip is local to the hook.
- N is capped on the frontend (≤ 6). Make the cap a single constant; do not hard-code
  it inline in the component.

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*
