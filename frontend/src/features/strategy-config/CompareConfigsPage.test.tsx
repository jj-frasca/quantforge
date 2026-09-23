// CompareConfigsPage: pick ONE strategy + symbol + date window, then add 2–6 param
// rows. Clicking "Run comparison" fans out N parallel POST /backtest calls (ADR-011)
// and renders an overlaid equity-curve chart + a comparison metrics table.
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import { server } from '../../test/server'
import { renderWithClient } from '../../test/utils'
import type { BacktestRequest, BacktestResponse } from '../../types/backtest'
import { CompareConfigsPage } from './CompareConfigsPage'

const responseFor = (sharpe: number, totalReturn: number): BacktestResponse => ({
  symbol: 'AAPL',
  strategy_name: 'sma_crossover',
  parameters: { fast: 20, slow: 50 },
  n_trades: 5,
  cost_rate: 0.001,
  metrics: {
    sharpe,
    max_drawdown: -0.12,
    total_return: totalReturn,
    annualized_return: totalReturn / 5,
    annualized_vol: 0.08,
    sortino: 1.9,
    calmar: 1.0,
  },
  equity_curve: [
    { timestamp_utc: '2020-01-01T00:00:00Z', equity: 100_000 },
    { timestamp_utc: '2024-01-01T00:00:00Z', equity: 100_000 * (1 + totalReturn) },
  ],
  buy_and_hold_curve: [
    { timestamp_utc: '2020-01-01T00:00:00Z', equity: 100_000 },
    { timestamp_utc: '2024-01-01T00:00:00Z', equity: 130_000 },
  ],
  buy_and_hold_total_return: 0.3,
  drawdown_curve: [{ timestamp_utc: '2020-01-01T00:00:00Z', drawdown: 0 }],
  rolling_sharpe_curve: [{ timestamp_utc: '2020-01-01T00:00:00Z', sharpe: 0 }],
  rolling_sharpe_window: 60,
  return_distribution: {
    bins: [{ bin_center: 0, frequency: 100 }],
    skewness: 0,
    kurtosis: 0,
  },
  trade_markers: [],
  benchmark_comparison: null,
})

test('renders the page with two default config rows', async () => {
  renderWithClient(<CompareConfigsPage />)
  expect(
    await screen.findByRole('group', { name: /^config A$/i }),
  ).toBeInTheDocument()
  // Two default rows so the user lands on a state that's immediately runnable
  // (one row degenerates to a normal backtest — not what this page is for).
  const rows = screen.getAllByRole('group', { name: /^config /i })
  expect(rows).toHaveLength(2)
  expect(screen.getByRole('button', { name: /run comparison/i })).toBeInTheDocument()
})

test('can add config rows up to the cap and remove down to the minimum', async () => {
  renderWithClient(<CompareConfigsPage />)
  await screen.findByRole('group', { name: /^config A$/i })

  // Adding rows: from 2 -> 6 (cap from ADR-011 §Decision).
  const addButton = screen.getByRole('button', { name: /add config/i })
  for (let i = 0; i < 4; i++) await userEvent.click(addButton)
  expect(screen.getAllByRole('group', { name: /^config /i })).toHaveLength(6)
  expect(addButton).toBeDisabled()

  // Removing rows: from 6 -> 2.
  const removeAll = () => screen.getAllByRole('button', { name: /^remove$/i })
  for (let i = 0; i < 4; i++) await userEvent.click(removeAll()[0])
  expect(screen.getAllByRole('group', { name: /^config /i })).toHaveLength(2)
  // At the floor, all remove buttons disable.
  for (const btn of removeAll()) expect(btn).toBeDisabled()
})

test('clicking Run comparison fans out N POSTs with each row params and renders the table', async () => {
  const seen: BacktestRequest[] = []
  let call = 0
  server.use(
    http.post('/api/v1/backtest', async ({ request }) => {
      seen.push((await request.json()) as BacktestRequest)
      // Distinct metrics per call so the table rows are individually identifiable.
      return HttpResponse.json(responseFor(0.5 + call * 0.5, 0.1 + call * 0.05))
      call++
    }),
  )

  renderWithClient(<CompareConfigsPage />)
  await screen.findByRole('group', { name: /^config A$/i })
  // Tweak row 1's "slow" so the two rows differ — important: if both rows are
  // identical, the test isn't actually proving fan-out, just N copies of the same call.
  const slows = screen.getAllByLabelText(/slow/i)
  await userEvent.clear(slows[1])
  await userEvent.type(slows[1], '100')

  await userEvent.click(screen.getByRole('button', { name: /run comparison/i }))
  // Wait for both responses to render their row in the table.
  await waitFor(() => {
    expect(screen.getByRole('table', { name: /comparison/i })).toBeInTheDocument()
  })
  const rows = screen.getAllByRole('row')
  // header + 2 data rows
  expect(rows).toHaveLength(3)
  expect(seen).toHaveLength(2)
  // Each request must carry that row's slow value.
  // strategy is { name: string; [k]: unknown } (passthrough schema), so `slow` reads as
  // unknown — assert the number rather than casting the whole object.
  const slowsSeen = seen.map((r) => r.strategy.slow as number).sort((a, b) => a - b)
  expect(slowsSeen).toEqual([50, 100])
})

test('editing symbol, dates, capital, and cost updates the submitted request', async () => {
  const seen: BacktestRequest[] = []
  server.use(
    http.post('/api/v1/backtest', async ({ request }) => {
      seen.push((await request.json()) as BacktestRequest)
      return HttpResponse.json(responseFor(0.5, 0.1))
    }),
  )

  renderWithClient(<CompareConfigsPage />)
  await screen.findByRole('group', { name: /^config A$/i })

  await userEvent.clear(screen.getByLabelText(/^symbol$/i))
  await userEvent.type(screen.getByLabelText(/^symbol$/i), 'msft')

  const startInput = screen.getByLabelText(/^start date$/i)
  await userEvent.clear(startInput)
  await userEvent.type(startInput, '2021-06-01')

  const endInput = screen.getByLabelText(/^end date$/i)
  await userEvent.clear(endInput)
  await userEvent.type(endInput, '2022-06-01')

  const capitalInput = screen.getByLabelText(/initial capital/i)
  await userEvent.clear(capitalInput)
  await userEvent.type(capitalInput, '50000')

  const costInput = screen.getByLabelText(/cost \(bps\)/i)
  await userEvent.clear(costInput)
  await userEvent.type(costInput, '25')

  await userEvent.click(screen.getByRole('button', { name: /run comparison/i }))
  await waitFor(() => expect(seen).toHaveLength(2))

  for (const request of seen) {
    expect(request.symbol).toBe('MSFT')
    expect(request.start_date).toBe('2021-06-01T00:00:00Z')
    expect(request.end_date).toBe('2022-06-01T00:00:00Z')
    expect(request.initial_capital).toBe(50000)
    expect(request.cost_rate).toBeCloseTo(25 / 10_000)
  }
})

test('switching strategy reseeds rows with the new strategy\'s own parameters', async () => {
  renderWithClient(<CompareConfigsPage />)
  await screen.findByRole('group', { name: /^config A$/i })

  // Default strategy is the catalog's first entry (sma: fast/slow).
  expect(screen.getAllByLabelText(/fast window/i)).toHaveLength(2)

  await userEvent.selectOptions(
    screen.getByRole('combobox', { name: /strategy/i }),
    'momentum',
  )

  // Old sma params are gone; momentum's own params (lookback/skip) render instead,
  // reseeded to that strategy's defaults on both existing rows.
  expect(screen.queryByLabelText(/fast window/i)).not.toBeInTheDocument()
  const lookbackInputs = screen.getAllByLabelText(/lookback window/i) as HTMLInputElement[]
  expect(lookbackInputs).toHaveLength(2)
  for (const input of lookbackInputs) expect(input.value).toBe('60')
})

test('a per-row failure surfaces only on that row — others still render metrics', async () => {
  // Row 0 fails, row 1 succeeds. The page's per-row error handling is the whole
  // point of ADR-011 §Decision — one bad config does not blank the comparison.
  let call = 0
  server.use(
    http.post('/api/v1/backtest', () => {
      const index = call++
      if (index === 0) {
        return HttpResponse.json({ detail: 'insufficient data' }, { status: 422 })
      }
      return HttpResponse.json(responseFor(0.8, 0.18))
    }),
  )

  renderWithClient(<CompareConfigsPage />)
  await screen.findByRole('group', { name: /^config A$/i })
  await userEvent.click(screen.getByRole('button', { name: /run comparison/i }))

  await waitFor(() => {
    expect(screen.getByRole('table', { name: /comparison/i })).toBeInTheDocument()
  })
  // Row 0 should render an error cell; row 1 should render a numeric Sharpe.
  expect(screen.getByText(/insufficient data/i)).toBeInTheDocument()
  // 0.80 is row 1's distinct Sharpe from the success response — proves it rendered
  // independently of row 0's failure.
  expect(screen.getByText('0.80')).toBeInTheDocument()
})
