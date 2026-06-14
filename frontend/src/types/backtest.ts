import { z } from 'zod'

// The strategy contract is owned by the BACKEND catalog (ADR-010): GET /api/v1/strategies
// + the Pydantic StrategyConfig discriminated union validate names + params on receipt.
// The frontend used to maintain its own three-strategy discriminated union here; that
// drifted the moment new strategies landed in the catalog and silently rejected every
// valid backtest submission at the boundary parse. We now accept any `{name, ...numbers}`
// shape and rely on:
//   1. the catalog-driven form to constrain `name` to known options and to provide
//      typed numeric inputs for each parameter, and
//   2. the backend to 422 on an unknown discriminator or out-of-range parameter.
// See ADR-010 §Consequences and feedback-frontend-shadow-validators memory.
//
// The TS type uses an index signature `number | string` so both the literal `name`
// field and any catalog-defined numeric param are accepted; Zod uses `passthrough()`
// which keeps unknown fields rather than stripping them.
export interface StrategyConfig {
  name: string
  [param: string]: number | string
}

export const strategyConfigSchema = z.object({ name: z.string().min(1) }).passthrough()

export const backtestRequestSchema = z.object({
  symbol: z.string().min(1),
  strategy: strategyConfigSchema,
  start_date: z.string(),
  end_date: z.string(),
  // Engine knobs (server-side defaults if omitted). Surfaced on the form so the user
  // can see what costs do to the equity curve. See api-contracts.md POST /backtest.
  initial_capital: z.number().positive().optional(),
  cost_rate: z.number().min(0).optional(),
})

export type BacktestRequest = z.infer<typeof backtestRequestSchema>

export const equityPointSchema = z.object({
  timestamp_utc: z.string(),
  equity: z.number(),
})

export type EquityPoint = z.infer<typeof equityPointSchema>

export const drawdownPointSchema = z.object({
  timestamp_utc: z.string(),
  drawdown: z.number().min(-1).max(0),
})

export type DrawdownPoint = z.infer<typeof drawdownPointSchema>

export const rollingSharpePointSchema = z.object({
  timestamp_utc: z.string(),
  sharpe: z.number(),
})

export type RollingSharpePoint = z.infer<typeof rollingSharpePointSchema>

export const returnBinSchema = z.object({
  bin_center: z.number(),
  frequency: z.number().int().nonnegative(),
})

export const returnDistributionSchema = z.object({
  bins: z.array(returnBinSchema),
  skewness: z.number(),
  kurtosis: z.number(),
})

export type ReturnBin = z.infer<typeof returnBinSchema>
export type ReturnDistribution = z.infer<typeof returnDistributionSchema>

export const backtestMetricsSchema = z.object({
  sharpe: z.number(),
  max_drawdown: z.number(),
  total_return: z.number(),
  annualized_return: z.number(),
  annualized_vol: z.number(),
})

export type BacktestMetricsView = z.infer<typeof backtestMetricsSchema>

export const tradeMarkerSchema = z.object({
  timestamp_utc: z.string(),
  direction: z.enum(['buy', 'sell']),
  equity: z.number(),
})

export type TradeMarker = z.infer<typeof tradeMarkerSchema>

export const backtestResponseSchema = z.object({
  symbol: z.string(),
  strategy_name: z.string(),
  parameters: z.record(z.string(), z.union([z.number(), z.number().int()])),
  n_trades: z.number().int().nonnegative(),
  cost_rate: z.number().nonnegative(),
  metrics: backtestMetricsSchema,
  equity_curve: z.array(equityPointSchema),
  buy_and_hold_curve: z.array(equityPointSchema),
  buy_and_hold_total_return: z.number(),
  drawdown_curve: z.array(drawdownPointSchema),
  rolling_sharpe_curve: z.array(rollingSharpePointSchema),
  rolling_sharpe_window: z.number().int().positive(),
  return_distribution: returnDistributionSchema,
  trade_markers: z.array(tradeMarkerSchema),
})

export type BacktestResponse = z.infer<typeof backtestResponseSchema>
