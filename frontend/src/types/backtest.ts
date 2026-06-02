import { z } from 'zod'

// Mirrors backend StrategyConfig (discriminated union on `name`).
// Keep field defaults aligned with backend defaults in case the UI ever wants them.
export const smaConfigSchema = z.object({
  name: z.literal('sma'),
  fast: z.number().int().min(1),
  slow: z.number().int().min(2),
})

export const momentumConfigSchema = z.object({
  name: z.literal('momentum'),
  lookback: z.number().int().min(1),
  skip: z.number().int().min(0),
})

export const meanReversionConfigSchema = z.object({
  name: z.literal('mean_reversion'),
  window: z.number().int().min(2),
  k: z.number().positive(),
})

export const strategyConfigSchema = z.discriminatedUnion('name', [
  smaConfigSchema,
  momentumConfigSchema,
  meanReversionConfigSchema,
])

export type StrategyConfig = z.infer<typeof strategyConfigSchema>

export const backtestRequestSchema = z.object({
  symbol: z.string().min(1),
  strategy: strategyConfigSchema,
  start_date: z.string(),
  end_date: z.string(),
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

export const backtestMetricsSchema = z.object({
  sharpe: z.number(),
  max_drawdown: z.number(),
  total_return: z.number(),
  annualized_return: z.number(),
  annualized_vol: z.number(),
})

export type BacktestMetricsView = z.infer<typeof backtestMetricsSchema>

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
})

export type BacktestResponse = z.infer<typeof backtestResponseSchema>
