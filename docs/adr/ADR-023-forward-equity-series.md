# ADR-023: Forward equity series on ForwardScore (dashboard equity curve)

- **Status**: Accepted
- **Date**: 2026-07-09
- **Deciders**: Joe Frasca
- **Extends**: ADR-019 (ForwardScore), ADR-020 (managed lifecycle), WP-D/WP-E (dashboard)

## Context
WP-E's "Live" dashboard is meant to show, per paper position, its **forward equity curve** vs
buy-and-hold. But `ForwardScore` (ADR-019) carries only *scalar* forward metrics
(`forward_return`, `forward_sharpe`, buy-and-hold twins, `beats_buy_and_hold`). There is no
per-bar series in the contract, so the dashboard could only draw a scalar comparison — not a
curve. Fabricating a curve from the scalars (e.g. a straight line to the terminal return) would
violate CLAUDE.md rule 6 (never imply structure the data doesn't have).

The series is already computed and thrown away: `evaluate_forward` runs the engine over the full
frame and slices the post-freeze forward returns (`fwd`) and buy-and-hold returns (`bh`). A
cumulative product of each **is** the honest forward equity curve on genuinely unseen data.

## Decision
Extend `ForwardScore` with an additive, defaulted `forward_equity: list[ForwardEquityPoint]`.
Each point is `(timestamp, strategy_equity, buy_and_hold_equity)` — a normalized equity **index
that starts at 1.0** at the freeze boundary and compounds each forward bar
(`(1 + returns).cumprod()`). Empty list when no forward bars have accrued.

- **Additive + defaulted** (`= []`), so existing persisted `data/paper_portfolio.json` scores
  (written before this change) still validate and simply carry an empty series until the next
  accrual run repopulates them. No migration, no data regeneration required.
- **Endpoint is unchanged.** WP-D's `GET /api/v1/paper-portfolio` has `response_model=
  list[PaperPosition]`, which embeds `ForwardScore` — the new field flows through automatically.
  This is the whole reason the extension lives on the model, not the route.
- **Float, not Decimal.** The equity index is a derived statistic, not a price that must
  round-trip exactly (backend-python money rule) — floats are correct here.

## Consequences
- The dashboard renders a real Recharts line per position (strategy vs buy-and-hold), reusing the
  existing equity-curve convention; positions with < 2 forward points fall back to the scalar
  comparison chart, and the "no forward data yet" note still holds for zero-bar positions.
- `scripts/paper.py` writes the series on every accrual with no code change (it persists whatever
  `evaluate_forward` returns). CRM + LOW currently have 1 forward bar → a 1-point series; the
  curve becomes meaningful as the forward test accrues over real calendar time (ADR-019's intent).
- The frontend Zod schema gains `forward_equity` as optional/defaulted — same
  don't-mirror-backend-invariants posture as the rest of `types/lab.ts`.

## Options considered
1. **Series on the model (chosen).** Minimal, additive, flows through the existing endpoint.
2. **Recompute the series in the read endpoint** (fetch bars + run engine on request). Rejected:
   couples the stateless read route to data-fetch + the engine (WP-D's explicit gotcha: "don't
   couple to a running hunt; just read the committed JSON").
3. **A new `/paper-portfolio/{symbol}/equity` endpoint.** Rejected: a second round-trip and a new
   contract for data the first call already has in hand.
