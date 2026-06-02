// Zod schemas: parse a valid backtest response; reject unknown discriminator, negative
// n_trades, missing metrics. Boundary validation of the /api/v1/backtest contract.
import { backtestResponseSchema, strategyConfigSchema } from './backtest'

const validResponse = {
  symbol: 'AAPL',
  strategy_name: 'sma_crossover',
  parameters: { fast: 5, slow: 20 },
  n_trades: 12,
  cost_rate: 0.001,
  metrics: {
    sharpe: 1.5,
    max_drawdown: -0.18,
    total_return: 0.42,
    annualized_return: 0.18,
    annualized_vol: 0.12,
  },
  equity_curve: [
    { timestamp_utc: '2024-01-01T00:00:00Z', equity: 100_000 },
    { timestamp_utc: '2024-01-02T00:00:00Z', equity: 100_500 },
  ],
  buy_and_hold_curve: [
    { timestamp_utc: '2024-01-01T00:00:00Z', equity: 100_000 },
    { timestamp_utc: '2024-01-02T00:00:00Z', equity: 100_200 },
  ],
  buy_and_hold_total_return: 0.32,
  drawdown_curve: [
    { timestamp_utc: '2024-01-01T00:00:00Z', drawdown: 0 },
    { timestamp_utc: '2024-01-02T00:00:00Z', drawdown: -0.05 },
  ],
  rolling_sharpe_curve: [
    { timestamp_utc: '2024-01-01T00:00:00Z', sharpe: 0 },
    { timestamp_utc: '2024-01-02T00:00:00Z', sharpe: 1.2 },
  ],
  rolling_sharpe_window: 60,
}

test('backtestResponseSchema parses a valid response', () => {
  expect(backtestResponseSchema.parse(validResponse)).toEqual(validResponse)
})

test('backtestResponseSchema rejects a negative n_trades', () => {
  expect(() => backtestResponseSchema.parse({ ...validResponse, n_trades: -1 })).toThrow()
})

test('backtestResponseSchema rejects missing metrics', () => {
  const bad: Record<string, unknown> = { ...validResponse }
  delete bad.metrics
  expect(() => backtestResponseSchema.parse(bad)).toThrow()
})

test('strategyConfigSchema parses each strategy variant', () => {
  expect(strategyConfigSchema.parse({ name: 'sma', fast: 5, slow: 20 })).toMatchObject({
    name: 'sma',
  })
  expect(
    strategyConfigSchema.parse({ name: 'momentum', lookback: 60, skip: 5 }),
  ).toMatchObject({ name: 'momentum' })
  expect(
    strategyConfigSchema.parse({ name: 'mean_reversion', window: 20, k: 2 }),
  ).toMatchObject({ name: 'mean_reversion' })
})

test('strategyConfigSchema rejects an unknown discriminator', () => {
  expect(() =>
    strategyConfigSchema.parse({ name: 'bogus', fast: 5, slow: 20 }),
  ).toThrow()
})
