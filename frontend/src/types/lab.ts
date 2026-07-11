import { z } from 'zod'

// Response contract OWNED BY THE BACKEND (WP-D, backend/app/api/v1/lab.py). These mirror the
// pydantic models LeaderboardRow (research/lab/universe.py) and PaperPosition + ForwardScore
// (research/lab/paper.py). We parse at the network boundary (frontend-typescript rule) but keep
// the schemas minimal — the backend is the single authority on shape
// (feedback-frontend-shadow-validators), so we validate only the fields the dashboard reads and
// do NOT re-encode backend invariants (e.g. no bounds on Sharpe). `status` is the one closed set
// we guard, because the UI branches on it.

export const leaderboardRowSchema = z.object({
  symbol: z.string(),
  strategy_name: z.string(),
  deflated_sharpe: z.number(),
  graduated: z.boolean(),
  // ADR-018: null for non-graduates (no holdout score / deflation verdict).
  holdout_sharpe: z.number().nullable().optional(),
  survives_universe_deflation: z.boolean().nullable().optional(),
})

export type LeaderboardRow = z.infer<typeof leaderboardRowSchema>

export const leaderboardSchema = z.array(leaderboardRowSchema)

// ADR-023 forward equity point: a normalized index (base 1.0) compounding each post-freeze bar.
export const forwardEquityPointSchema = z.object({
  timestamp: z.string(),
  strategy_equity: z.number(),
  buy_and_hold_equity: z.number(),
})

export type ForwardEquityPoint = z.infer<typeof forwardEquityPointSchema>

// ADR-019 forward score: scalar metrics + the ADR-023 per-bar `forward_equity` series (defaulted
// so scores persisted before ADR-023 still parse). `beats_buy_and_hold` is the honest bar.
export const forwardScoreSchema = z.object({
  forward_bars: z.number().int().nonnegative(),
  forward_return: z.number(),
  forward_sharpe: z.number(),
  buy_and_hold_return: z.number(),
  buy_and_hold_sharpe: z.number(),
  beats_buy_and_hold: z.boolean(),
  as_of: z.string(),
  forward_equity: z.array(forwardEquityPointSchema).default([]),
})

export type ForwardScore = z.infer<typeof forwardScoreSchema>

export const paperPositionSchema = z.object({
  symbol: z.string(),
  strategy_name: z.string(),
  parameters: z.record(z.string(), z.union([z.number(), z.number().int()])),
  frozen_at: z.string(),
  score: forwardScoreSchema.nullable().optional(),
  // Lifecycle (ADR-020): managed positions close automatically when the edge decays.
  status: z.enum(['open', 'closed']),
  closed_at: z.string().nullable().optional(),
  exit_reasons: z.array(z.string()),
})

export type PaperPosition = z.infer<typeof paperPositionSchema>

export const paperPortfolioSchema = z.array(paperPositionSchema)
