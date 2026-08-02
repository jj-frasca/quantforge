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

// Graduates view (backend/app/api/v1/graduates.py): the research-pool experiments that cleared the
// gate, best-first. A projection of the leaderboard restricted to graduates (no `graduated` field —
// every row is, by construction). We validate only what the panel reads.
export const graduateRowSchema = z.object({
  symbol: z.string(),
  strategy_name: z.string(),
  deflated_sharpe: z.number(),
  holdout_sharpe: z.number().nullable().optional(),
  survives_universe_deflation: z.boolean().nullable().optional(),
  // ADR-023: null when value was off or the name is unscorable (e.g. an ETF with no 10-K).
  undervaluation_score: z.number().nullable().optional(),
})

export type GraduateRow = z.infer<typeof graduateRowSchema>

export const graduatesSchema = z.array(graduateRowSchema)

// Cross-sectional view (backend/app/api/v1/cross_sectional.py, ADR-024): the latest cross-sectional
// hunt — its per-strategy finalists, graduation verdict, and universe size. `null` when no hunt has
// produced a record yet (an empty/missing pool is a normal answer, not an error).
export const crossSectionalTrialSchema = z.object({
  strategy_name: z.string(),
  observed_sharpe: z.number(),
  deflated_sharpe: z.number(),
  pbo: z.number(),
  parameter_stability_score: z.number(),
})

export type CrossSectionalTrial = z.infer<typeof crossSectionalTrialSchema>

export const crossSectionalViewSchema = z.object({
  created_at: z.string(),
  universe_size: z.number().int().nonnegative(),
  best_strategy_name: z.string().nullable().optional(),
  graduated: z.boolean(),
  graduate_holdout_sharpe: z.number().nullable().optional(),
  trials: z.array(crossSectionalTrialSchema),
})

export type CrossSectionalView = z.infer<typeof crossSectionalViewSchema>

// The endpoint returns the view object or null (no hunt yet).
export const crossSectionalResponseSchema = crossSectionalViewSchema.nullable()

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
