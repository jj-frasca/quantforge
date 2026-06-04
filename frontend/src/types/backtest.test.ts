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
  return_distribution: {
    bins: [
      { bin_center: -0.01, frequency: 3 },
      { bin_center: 0.0, frequency: 50 },
      { bin_center: 0.01, frequency: 12 },
    ],
    skewness: -0.2,
    kurtosis: 1.1,
  },
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

test('strategyConfigSchema accepts any name (backend is the discriminator authority)', () => {
  // The frontend used to hardcode the three original variants here and silently rejected
  // every new catalog strategy at the boundary. The contract is now: the backend catalog
  // owns the list of valid names; the frontend trusts whatever the catalog-driven form
  // selects and lets the backend 422 anything truly invalid (ADR-010 §Consequences).
  expect(
    strategyConfigSchema.parse({ name: 'rsi_mean_reversion', window: 14, oversold: 30 }),
  ).toMatchObject({ name: 'rsi_mean_reversion' })
  expect(
    strategyConfigSchema.parse({ name: 'keltner_channel', ma_window: 20 }),
  ).toMatchObject({ name: 'keltner_channel' })
})

test('strategyConfigSchema rejects a missing or empty name', () => {
  // The one thing we DO enforce: there must be a non-empty name. Everything else is
  // delegated to the backend.
  expect(() => strategyConfigSchema.parse({ name: '', fast: 5 })).toThrow()
  expect(() => strategyConfigSchema.parse({ fast: 5, slow: 20 })).toThrow()
})
