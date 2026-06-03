// BacktestResultsPage: form defaults; submit sends the discriminated strategy body;
// changing the strategy swaps the visible param fields; success renders the result.
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
    bins: [
      { bin_center: 0, frequency: 1000 },
    ],
    skewness: 0,
    kurtosis: 0.5,
  },
}

test('renders the form with sensible defaults', () => {
  renderWithClient(<BacktestResultsPage />)
  expect(screen.getByLabelText(/symbol/i)).toHaveValue('AAPL')
  expect(screen.getByLabelText(/^strategy$/i)).toHaveValue('sma')
  expect(screen.getByLabelText(/fast/i)).toHaveValue(20)
  expect(screen.getByLabelText(/slow/i)).toHaveValue(50)
})

test('changing strategy swaps the visible param fields', async () => {
  renderWithClient(<BacktestResultsPage />)
  await userEvent.selectOptions(screen.getByLabelText(/^strategy$/i), 'momentum')
  expect(screen.queryByLabelText(/fast/i)).not.toBeInTheDocument()
  expect(screen.getByLabelText(/lookback/i)).toHaveValue(60)
  expect(screen.getByLabelText(/skip/i)).toHaveValue(5)

  await userEvent.selectOptions(screen.getByLabelText(/^strategy$/i), 'mean_reversion')
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
  await userEvent.click(screen.getByRole('button', { name: /run backtest/i }))

  expect(await screen.findByLabelText('backtest result')).toBeInTheDocument()
  expect(screen.getByLabelText('equity curve')).toBeInTheDocument()
  expect(body).toEqual({
    symbol: 'AAPL',
    strategy: { name: 'sma', fast: 20, slow: 50 },
    start_date: '2020-01-01T00:00:00Z',
    end_date: '2024-01-01T00:00:00Z',
  })
})

test('typing into a strategy param field updates the form state', async () => {
  let body: unknown
  server.use(
    http.post('/api/v1/backtest', async ({ request }) => {
      body = await request.json()
      return HttpResponse.json(successResponse)
    }),
  )
  renderWithClient(<BacktestResultsPage />)

  // SMA params
  const fast = screen.getByLabelText(/fast/i)
  await userEvent.clear(fast)
  await userEvent.type(fast, '7')

  // Switch to momentum and tweak its params
  await userEvent.selectOptions(screen.getByLabelText(/^strategy$/i), 'momentum')
  const lookback = screen.getByLabelText(/lookback/i)
  await userEvent.clear(lookback)
  await userEvent.type(lookback, '30')

  // Switch to mean_reversion and tweak its params
  await userEvent.selectOptions(screen.getByLabelText(/^strategy$/i), 'mean_reversion')
  const window = screen.getByLabelText(/window/i)
  await userEvent.clear(window)
  await userEvent.type(window, '15')

  // Also flex the symbol + date onChange handlers
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

test('surfaces the backend detail when the backtest fails', async () => {
  server.use(
    http.post('/api/v1/backtest', () =>
      HttpResponse.json({ detail: 'insufficient data' }, { status: 422 }),
    ),
  )
  renderWithClient(<BacktestResultsPage />)
  await userEvent.click(screen.getByRole('button', { name: /run backtest/i }))
  await waitFor(() => {
    expect(screen.getByRole('alert')).toHaveTextContent(/insufficient data/i)
  })
})
