// BacktestResultsPage: form renders from the strategy catalog (loaded via MSW); switching
// strategy swaps params; submitting POSTs the discriminated body; failure surfaces the
// backend `detail`. The catalog itself is the test/server.ts default.
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import { server } from '../../test/server'
import { renderWithClient } from '../../test/utils'
import type { BacktestResponse } from '../../types/backtest'
import { BacktestResultsPage } from './BacktestResultsPage'

const successResponse: BacktestResponse = {
  symbol: 'AAPL',
  strategy_name: 'sma_crossover',
  parameters: { fast: 20, slow: 50 },
  n_trades: 8,
  cost_rate: 0.001,
  metrics: {
    sharpe: 1.1,
    max_drawdown: -0.12,
    total_return: 0.18,
    annualized_return: 0.09,
    annualized_vol: 0.08,
  },
  equity_curve: [
    { timestamp_utc: '2020-01-01T00:00:00Z', equity: 100_000 },
    { timestamp_utc: '2024-01-01T00:00:00Z', equity: 118_000 },
  ],
  buy_and_hold_curve: [
    { timestamp_utc: '2020-01-01T00:00:00Z', equity: 100_000 },
    { timestamp_utc: '2024-01-01T00:00:00Z', equity: 130_000 },
  ],
  buy_and_hold_total_return: 0.3,
  drawdown_curve: [
    { timestamp_utc: '2020-01-01T00:00:00Z', drawdown: 0 },
    { timestamp_utc: '2024-01-01T00:00:00Z', drawdown: -0.08 },
  ],
  rolling_sharpe_curve: [
    { timestamp_utc: '2020-01-01T00:00:00Z', sharpe: 0 },
    { timestamp_utc: '2024-01-01T00:00:00Z', sharpe: 1.1 },
  ],
  rolling_sharpe_window: 60,
  return_distribution: {
    bins: [{ bin_center: 0, frequency: 1000 }],
    skewness: 0,
    kurtosis: 0.5,
  },
  trade_markers: [],
}

test('renders the form with catalog-driven defaults once strategies load', async () => {
  renderWithClient(<BacktestResultsPage />)
  // Catalog fetch is async — wait for it to land.
  expect(await screen.findByLabelText(/symbol/i)).toHaveValue('AAPL')
  expect(screen.getByLabelText(/^strategy$/i)).toHaveValue('sma')
  expect(screen.getByLabelText(/fast/i)).toHaveValue(20)
  expect(screen.getByLabelText(/slow/i)).toHaveValue(50)
})

test('changing strategy swaps the visible param fields', async () => {
  renderWithClient(<BacktestResultsPage />)
  const strategySelect = await screen.findByLabelText(/^strategy$/i)

  await userEvent.selectOptions(strategySelect, 'momentum')
  expect(screen.queryByLabelText(/fast/i)).not.toBeInTheDocument()
  expect(screen.getByLabelText(/lookback/i)).toHaveValue(60)
  expect(screen.getByLabelText(/skip/i)).toHaveValue(5)

  await userEvent.selectOptions(strategySelect, 'mean_reversion')
  expect(screen.queryByLabelText(/lookback/i)).not.toBeInTheDocument()
  expect(screen.getByLabelText(/window/i)).toHaveValue(20)
})

test('submitting sends the discriminated body and renders the result', async () => {
  let body: unknown
  server.use(
    http.post('/api/v1/backtest', async ({ request }) => {
      body = await request.json()
      return HttpResponse.json(successResponse)
    }),
  )
  renderWithClient(<BacktestResultsPage />)
  await userEvent.click(await screen.findByRole('button', { name: /run backtest/i }))

  expect(await screen.findByLabelText('backtest result')).toBeInTheDocument()
  expect(screen.getByLabelText('equity curve')).toBeInTheDocument()
  expect(body).toEqual({
    symbol: 'AAPL',
    strategy: { name: 'sma', fast: 20, slow: 50 },
    start_date: '2020-01-01T00:00:00Z',
    end_date: '2024-01-01T00:00:00Z',
    // Engine knobs land in the wire payload at their form defaults: $100k capital and
    // 10 bps cost (10 / 10_000 = 0.001 fraction — the backend's canonical form).
    initial_capital: 100_000,
    cost_rate: 0.001,
  })
})

test('overriding initial capital and cost on the form propagates to the request body', async () => {
  // The build catch behind this test: HTML5 `min` + `step` were a footgun on the cost
  // input. With min=1 and step=1000, a default value of 100_000 violated the
  // constraint `value = min + n*step`; userEvent silently swallowed the submit and
  // none of the existing tests rendered a result. We use step="any" + min to keep
  // sensible bounds without the divisibility trap. See
  // [[feedback-quantforge-ci-discipline]] in auto-memory.
  let body: { initial_capital?: number; cost_rate?: number } | undefined
  server.use(
    http.post('/api/v1/backtest', async ({ request }) => {
      body = (await request.json()) as typeof body
      return HttpResponse.json(successResponse)
    }),
  )
  renderWithClient(<BacktestResultsPage />)
  const capitalInput = await screen.findByLabelText(/initial capital/i)
  await userEvent.clear(capitalInput)
  await userEvent.type(capitalInput, '250000')
  const costInput = screen.getByLabelText(/cost \(bps\)/i)
  await userEvent.clear(costInput)
  await userEvent.type(costInput, '5')

  await userEvent.click(screen.getByRole('button', { name: /run backtest/i }))
  await screen.findByLabelText('backtest result')
  expect(body?.initial_capital).toBe(250_000)
  // 5 bps -> 0.0005 fraction. The bps-to-fraction conversion is the form's
  // responsibility, not the backend's.
  expect(body?.cost_rate).toBe(0.0005)
})

test('typing into a catalog-driven param field updates the form state', async () => {
  let body: unknown
  server.use(
    http.post('/api/v1/backtest', async ({ request }) => {
      body = await request.json()
      return HttpResponse.json(successResponse)
    }),
  )
  renderWithClient(<BacktestResultsPage />)
  const strategySelect = await screen.findByLabelText(/^strategy$/i)

  // SMA: tweak fast
  const fast = screen.getByLabelText(/fast/i)
  await userEvent.clear(fast)
  await userEvent.type(fast, '7')

  // Switch to momentum and tweak its params
  await userEvent.selectOptions(strategySelect, 'momentum')
  const lookback = screen.getByLabelText(/lookback/i)
  await userEvent.clear(lookback)
  await userEvent.type(lookback, '30')

  // Switch to mean_reversion and tweak its params
  await userEvent.selectOptions(strategySelect, 'mean_reversion')
  const window = screen.getByLabelText(/window/i)
  await userEvent.clear(window)
  await userEvent.type(window, '15')

  // Edit symbol too
  const symbol = screen.getByLabelText(/symbol/i)
  await userEvent.clear(symbol)
  await userEvent.type(symbol, 'msft')

  await userEvent.click(screen.getByRole('button', { name: /run backtest/i }))
  await waitFor(() => {
    expect(body).toMatchObject({
      symbol: 'MSFT',
      strategy: { name: 'mean_reversion', window: 15 },
    })
  })
})

test('shows the selected strategy description and citations', async () => {
  renderWithClient(<BacktestResultsPage />)
  await screen.findByLabelText(/symbol/i)
  expect(screen.getByText(/trend-following baseline/i)).toBeInTheDocument()
})

test('submitting each catalog strategy reaches the backend (no client-side discriminated-union drift)', async () => {
  // Regression: the frontend used to mirror the backend StrategyConfig as a Zod
  // discriminated union with only sma/momentum/mean_reversion variants. Every new
  // strategy that landed in the backend catalog silently failed the submit-time parse
  // on the frontend. This test exercises every catalog variant against a
  // canned-success handler — they all must reach the network.
  const bodiesSeen: string[] = []
  server.use(
    http.post('/api/v1/backtest', async ({ request }) => {
      const body = (await request.json()) as { strategy: { name: string } }
      bodiesSeen.push(body.strategy.name)
      return HttpResponse.json(successResponse)
    }),
  )
  renderWithClient(<BacktestResultsPage />)
  const strategySelect = await screen.findByLabelText(/^strategy$/i)

  for (const name of ['sma', 'momentum', 'mean_reversion'] as const) {
    await userEvent.selectOptions(strategySelect, name)
    await userEvent.click(screen.getByRole('button', { name: /run backtest/i }))
    await waitFor(() => {
      expect(bodiesSeen.at(-1)).toBe(name)
    })
  }
})

test('surfaces the backend detail when the backtest fails', async () => {
  server.use(
    http.post('/api/v1/backtest', () =>
      HttpResponse.json({ detail: 'insufficient data' }, { status: 422 }),
    ),
  )
  renderWithClient(<BacktestResultsPage />)
  await userEvent.click(await screen.findByRole('button', { name: /run backtest/i }))
  await waitFor(() => {
    expect(screen.getByRole('alert')).toHaveTextContent(/insufficient data/i)
  })
})
