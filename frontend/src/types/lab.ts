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
// `ic_*` (ADR-035) is the per-date rank correlation between the signal and next-period returns —
// whether the RANKING carried information, which the Sharpe columns cannot distinguish from a
// couple of names carrying the P&L. Optional: trials recorded before ADR-035 were never measured.
export const crossSectionalTrialSchema = z.object({
  strategy_name: z.string(),
  observed_sharpe: z.number(),
  deflated_sharpe: z.number(),
  pbo: z.number(),
  parameter_stability_score: z.number(),
  ic_mean: z.number().nullable().optional(),
  ic_t_stat: z.number().nullable().optional(),
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

// Equity-curve view (backend/app/api/v1/equity-curve, model app/execution/equity_curve.py): one
// dated snapshot of the REAL paper account — absolute equity/cash, position count, and the cumulative
// return since the $100k paper starting equity. Oldest-first. This is the headline "are we making
// money?" series; we validate only what the panel reads and let the backend own the shape.
export const equityPointSchema = z.object({
  timestamp: z.string(),
  equity: z.number(),
  cash: z.number(),
  n_positions: z.number().int().nonnegative(),
  return_since_start: z.number(),
})

export type EquityPoint = z.infer<typeof equityPointSchema>

export const equityCurveSchema = z.array(equityPointSchema)

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

// Pool report (backend/app/api/v1/lab.py, ADR-033): the honest headline over the whole research
// programme. The number that matters is `n_surviving_deflation` out of `n_leaderboard_graduates` —
// how many graduates are distinguishable from best-of-N selection luck. `near_misses` carries each
// candidate's OWN bar, because the bar depends on that candidate's holdout length.
export const nearMissSchema = z.object({
  symbol: z.string(),
  strategy_name: z.string(),
  holdout_sharpe: z.number(),
  bar: z.number(),
  ratio_to_bar: z.number(),
  holdout_years: z.number(),
})

export type NearMiss = z.infer<typeof nearMissSchema>

export const deflationCohortsSchema = z.object({
  n_survivors: z.number().int(),
  n_non_survivors: z.number().int(),
  n_unknown: z.number().int(),
  survivor_mean_forward_sharpe: z.number().nullable().optional(),
  non_survivor_mean_forward_sharpe: z.number().nullable().optional(),
})

export type DeflationCohorts = z.infer<typeof deflationCohortsSchema>

// ADR-043: what an edge must BE for the pipeline to detect it, beside the bar an observation must
// clear. `bar` is what must be OBSERVED; `detectable_sharpe` is the TRUE annualized Sharpe that
// clears it with probability `power`. Their difference is estimation noise — which is why an edge
// sitting exactly at the bar is a coin flip, not a graduate. Null when no graduate fixes a holdout
// length to quote it at.
export const detectionFrontierSchema = z.object({
  n_symbols: z.number().int(),
  holdout_years: z.number(),
  power: z.number(),
  bar: z.number(),
  detectable_sharpe: z.number(),
  standard_error: z.number(),
})

export type DetectionFrontier = z.infer<typeof detectionFrontierSchema>

export const poolReportSchema = z.object({
  n_experiments: z.number().int(),
  n_symbols: z.number().int(),
  n_trials: z.number().int(),
  n_graduate_experiments: z.number().int(),
  n_leaderboard_graduates: z.number().int(),
  n_surviving_deflation: z.number().int(),
  near_misses: z.array(nearMissSchema),
  n_open_positions: z.number().int(),
  frontier: detectionFrontierSchema.nullable().default(null),
  book: deflationCohortsSchema,
})

export type PoolReport = z.infer<typeof poolReportSchema>

// The gate's measured behaviour on symbols with NO EDGE by construction (ADR-036/037), written by
// the null-calibration workflow. `false_graduation_rate` is a Type-I error for the WHOLE pipeline —
// search, DSR, PBO, MinTRL, holdout and beat-buy-and-hold together — which no single component's
// guarantee implies. It is a property of `gate_config_version`; re-measured whenever the gate moves.
export const nullCalibrationSchema = z.object({
  n_symbols: z.number().int(),
  n_graduates: z.number().int(),
  false_graduation_rate: z.number().min(0).max(1),
  n_clear_deflation_bar: z.number().int(),
  deflation_bar: z.number(),
  max_deflated_sharpe: z.number(),
  max_holdout_sharpe: z.number().nullable(),
  holdout_years: z.array(z.number()).default([]),
  walk_forward_oos_sharpes: z.array(z.number()).default([]),
  purged_cv_oos_sharpes: z.array(z.number()).default([]),
  gate_config_version: z.string(),
  null_mode: z.string(),
})

export type NullCalibration = z.infer<typeof nullCalibrationSchema>
