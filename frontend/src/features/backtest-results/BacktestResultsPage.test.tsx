// BacktestResultsPage: form renders from the strategy catalog (loaded via MSW); switching
// strategy swaps params; submitting POSTs the discriminated body; failure surfaces the
// backend `detail`. The catalog itself is the test/server.ts default.
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach } from 'vitest'

import { useAppShell } from '../../state/appShell'
import { server } from '../../test/server'
import { renderWithClient } from '../../test/utils'
import type { BacktestResponse } from '../../types/backtest'
import { BacktestResultsPage } from './BacktestResultsPage'

beforeEach(() => {
  useAppShell.setState({ activePage: 'data-explorer', pendingValidation: null })
})

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
  // Dates come from defaultDateRange(5) anchored to "today" — we don't pin the wall
  // clock here (defaultDateRange has its own test). Use toMatchObject and verify the
  // date shape separately.
  expect(body).toMatchObject({
    symbol: 'AAPL',
    strategy: { name: 'sma', fast: 20, slow: 50 },
    // Engine knobs land in the wire payload at their form defaults: $100k capital and
    // 10 bps cost (10 / 10_000 = 0.001 fraction — the backend's canonical form).
    initial_capital: 100_000,
    cost_rate: 0.001,
  })
  // Dates are YYYY-MM-DDT00:00:00Z ISO strings; end_date is today (or close enough),
  // start_date is 5 calendar years earlier.
  const dateRe = /^\d{4}-\d{2}-\d{2}T00:00:00Z$/
  const wireBody = body as { start_date: string; end_date: string }
  expect(wireBody.start_date).toMatch(dateRe)
  expect(wireBody.end_date).toMatch(dateRe)
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

test('shows a friendly nudge so a beginner knows defaults are sane and Run is the next step', async () => {
  // The "democratize" rule: a 7-field form is intimidating even when every field is
  // pre-populated. The nudge above the form says explicitly that one click is enough.
  renderWithClient(<BacktestResultsPage />)
  await screen.findByLabelText(/^strategy$/i)
  expect(
    screen.getByText(/every field below is pre-filled with sensible defaults/i),
  ).toBeInTheDocument()
})

test('clicking a preset card loads its symbol + strategy + params into the form', async () => {
  // Track what hits the wire. The preset under test is "SMA crossover on SPY" — when
  // the user clicks Load, the form must repaint with symbol=SPY and strategy=sma with
  // the preset's fast/slow, and submitting then sends that body. This is the whole
  // value prop of presets: one click goes from "I don't know what to type" to "I have
  // a result on screen."
  let body: { symbol?: string; strategy?: { name: string; fast?: number; slow?: number } } = {}
  server.use(
    http.post('/api/v1/backtest', async ({ request }) => {
      body = (await request.json()) as typeof body
      return HttpResponse.json(successResponse)
    }),
  )
  renderWithClient(<BacktestResultsPage />)
  await screen.findByLabelText(/^strategy$/i)
  const presetLoadButtons = screen.getAllByRole('button', { name: /load this preset/i })
  // First card is SMA on SPY (Slate 3 ordering).
  await userEvent.click(presetLoadButtons[0])
  expect(screen.getByLabelText(/symbol/i)).toHaveValue('SPY')
  expect(screen.getByLabelText(/^strategy$/i)).toHaveValue('sma')
  expect(screen.getByLabelText(/fast/i)).toHaveValue(50)
  expect(screen.getByLabelText(/slow/i)).toHaveValue(200)
  await userEvent.click(screen.getByRole('button', { name: /run backtest/i }))
  await waitFor(() => {
    expect(body.symbol).toBe('SPY')
    expect(body.strategy).toMatchObject({ name: 'sma', fast: 50, slow: 200 })
  })
})

test('shows the strategy summary above the longer description so a beginner gets it at a glance', async () => {
  // The "democratize" rule: the at-a-glance face of each strategy is the plain-English
  // summary, not the implementation-nuance description. We assert the summary copy
  // (from the test/server.ts default catalog for SMA) lands on screen the moment a
  // strategy is selected.
  renderWithClient(<BacktestResultsPage />)
  await screen.findByLabelText(/^strategy$/i)
  const info = screen.getByLabelText('strategy info')
  expect(info).toHaveTextContent(/recent average has been rising/i)
})

test('clicking "Validate this strategy" after a backtest hands off to Validation', async () => {
  // Symmetric with the per-row Validate button on Compare Configs — closes the same
  // methodology arc from the single-backtest workflow. After a successful backtest,
  // the post-result bridge offers to take the user into PBO + Deflated Sharpe with
  // the current (symbol, strategy, dates) pre-filled.
  server.use(
    http.post('/api/v1/backtest', () => HttpResponse.json(successResponse)),
  )
  renderWithClient(<BacktestResultsPage />)
  await userEvent.click(await screen.findByRole('button', { name: /run backtest/i }))
  await screen.findByLabelText('backtest result')
  await userEvent.click(screen.getByRole('button', { name: /validate this strategy/i }))
  const state = useAppShell.getState()
  expect(state.activePage).toBe('validation')
  expect(state.pendingValidation?.symbol).toBe('AAPL')
  expect(state.pendingValidation?.strategy).toBe('sma')
})
