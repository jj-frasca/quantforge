import userEvent from '@testing-library/user-event'
import { screen, within, waitForElementToBeRemoved } from '@testing-library/react'
import { http, HttpResponse } from 'msw'

import { server } from '../../test/server'
import { renderWithClient } from '../../test/utils'
import { GraduatesPanel } from './GraduatesPanel'

const graduates = [
  {
    symbol: 'CRM',
    strategy_name: 'trend_filtered_mean_reversion',
    deflated_sharpe: 0.44,
    holdout_sharpe: 0.5,
    survives_universe_deflation: true,
    undervaluation_score: 0.7,
  },
  {
    symbol: 'LOW',
    strategy_name: 'rsi_mean_reversion',
    deflated_sharpe: 0.3,
    holdout_sharpe: 0.2,
    survives_universe_deflation: false,
    undervaluation_score: null,
  },
]

test('renders the graduates table with symbol, strategy and deflation verdict', async () => {
  server.use(http.get('/api/v1/graduates', () => HttpResponse.json(graduates)))
  renderWithClient(<GraduatesPanel />)

  expect(await screen.findByRole('cell', { name: 'CRM' })).toBeInTheDocument()
  expect(screen.getByRole('cell', { name: 'trend_filtered_mean_reversion' })).toBeInTheDocument()
  // Honest cross-symbol-selection caveat surfaces per row.
  expect(screen.getByText('survives')).toBeInTheDocument()
  expect(screen.getByText('selection-lucky')).toBeInTheDocument()
  // Undervaluation renders as a percentage, em dash when unscorable.
  expect(screen.getByText('70%')).toBeInTheDocument()
  expect(screen.getByText('2 graduates · 1 survives universe deflation')).toBeInTheDocument()
})

test('shows a dash for the deflation verdict on a graduate that predates it', async () => {
  server.use(
    http.get('/api/v1/graduates', () =>
      HttpResponse.json([{ ...graduates[0], survives_universe_deflation: null }]),
    ),
  )
  renderWithClient(<GraduatesPanel />)

  expect(await screen.findByRole('cell', { name: 'CRM' })).toBeInTheDocument()
  expect(screen.getByText('—')).toBeInTheDocument()
  expect(screen.queryByText('survives')).not.toBeInTheDocument()
  expect(screen.queryByText('selection-lucky')).not.toBeInTheDocument()
})

test('renders the empty state when no strategy has graduated', async () => {
  server.use(http.get('/api/v1/graduates', () => HttpResponse.json([])))
  renderWithClient(<GraduatesPanel />)

  expect(await screen.findByText(/no strategy has cleared the gate/i)).toBeInTheDocument()
})

test('renders an em dash for a graduate with no holdout Sharpe yet', async () => {
  // Both fixture rows above always carry a holdout_sharpe — a graduate that has
  // cleared the gate but not yet reached the locked holdout evaluation never hit
  // fmtSharpe's null branch.
  server.use(
    http.get('/api/v1/graduates', () =>
      HttpResponse.json([{ ...graduates[0], holdout_sharpe: null }]),
    ),
  )
  renderWithClient(<GraduatesPanel />)

  expect(await screen.findByRole('cell', { name: 'CRM' })).toBeInTheDocument()
  expect(screen.getAllByRole('cell', { name: '—' })).toHaveLength(1)
})

test('shows an error message when the graduates endpoint fails', async () => {
  server.use(http.get('/api/v1/graduates', () => new HttpResponse(null, { status: 500 })))
  renderWithClient(<GraduatesPanel />)

  expect(await screen.findByText(/could not load graduates/i)).toBeInTheDocument()
})

test('shows a loading indicator while the graduates are pending', async () => {
  server.use(http.get('/api/v1/graduates', () => HttpResponse.json(graduates)))
  renderWithClient(<GraduatesPanel />)

  await waitForElementToBeRemoved(() => screen.queryByText(/loading graduates/i))
  expect(await screen.findByRole('cell', { name: 'CRM' })).toBeInTheDocument()
})

const dcfSettings = {
  discount_rate: 0.1, terminal_growth: 0.025,
  min_growth: 0, max_growth: 0.12, projection_years: '5',
}

test('discloses recorded DCF settings in a collapsed native disclosure with semantic labels', async () => {
  server.use(http.get('/api/v1/graduates', () => HttpResponse.json([
    { ...graduates[0], dcf_assumptions: dcfSettings },
  ])))
  renderWithClient(<GraduatesPanel />)
  const summary = await screen.findByText('Recorded DCF settings')
  const details = summary.closest('details')!
  expect(details).not.toHaveAttribute('open')
  expect(within(details).getAllByRole('term', { hidden: true })).toHaveLength(5)
  expect(within(details).getAllByRole('definition', { hidden: true })).toHaveLength(5)
  await userEvent.click(summary)
  expect(details).toHaveAttribute('open')
  expect(within(details).getByText('Discount rate')).toBeVisible()
  expect(within(details).getByText('10%')).toBeVisible()
  expect(within(details).getByText('Terminal growth')).toBeVisible()
  expect(within(details).getByText('2.5%')).toBeVisible()
  expect(within(details).getByText('Minimum growth bound')).toBeVisible()
  expect(within(details).getByText('0%')).toBeVisible()
  expect(within(details).getByText('Maximum growth bound')).toBeVisible()
  expect(within(details).getByText('12%')).toBeVisible()
  expect(within(details).getByText('Projection years')).toBeVisible()
  expect(within(details).getByText('5')).toBeVisible()
  expect(within(details).getByText(/recorded settings alone do not reproduce or validate the score/i)).toBeVisible()
  expect(screen.getByText('70%')).toBeVisible()
  expect(screen.getByText('survives')).toBeVisible()
})

test.each([undefined, null])('shows explicit unknown settings with a present score: %s', async (dcf_assumptions) => {
  server.use(http.get('/api/v1/graduates', () => HttpResponse.json([
    { ...graduates[0], dcf_assumptions },
  ])))
  renderWithClient(<GraduatesPanel />)
  expect(await screen.findByText('DCF settings not recorded')).toBeVisible()
  expect(screen.getByText('70%')).toBeVisible()
  expect(screen.queryByText('Recorded DCF settings')).not.toBeInTheDocument()
})

test.each(['0', '-5', '900719925474099312345678901234567890'])('shows exact horizon %s even when valuation is unscorable', async (projection_years) => {
  server.use(http.get('/api/v1/graduates', () => HttpResponse.json([
    { ...graduates[0], undervaluation_score: null,
      dcf_assumptions: { ...dcfSettings, projection_years } },
  ])))
  renderWithClient(<GraduatesPanel />)
  const summary = await screen.findByText('Recorded DCF settings')
  await userEvent.click(summary)
  expect(screen.getByText(projection_years)).toBeVisible()
  expect(screen.getByText('—')).toBeVisible()
  expect(screen.queryByText('DCF settings not recorded')).not.toBeInTheDocument()
})

test('formats finite extreme settings without overflow or reordering growth bounds', async () => {
  server.use(http.get('/api/v1/graduates', () => HttpResponse.json([
    { ...graduates[0], dcf_assumptions: {
      ...dcfSettings, discount_rate: Number.MAX_VALUE, terminal_growth: -Number.MAX_VALUE,
      min_growth: 0.7, max_growth: -0.4,
    } },
  ])))
  renderWithClient(<GraduatesPanel />)
  const summary = await screen.findByText('Recorded DCF settings')
  await userEvent.click(summary)
  const details = summary.closest('details')!
  const formatter = new Intl.NumberFormat('en-US', { style: 'percent', maximumSignificantDigits: 6 })
  expect(within(details).getByText(formatter.format(Number.MAX_VALUE))).toBeVisible()
  expect(within(details).getByText(formatter.format(-Number.MAX_VALUE))).toBeVisible()
  expect(within(details).getByText('70%')).toBeVisible()
  expect(within(details).getByText('-40%')).toBeVisible()
  expect(details.textContent).not.toMatch(/Infinity|NaN/)
})

test('rejects malformed present settings through the existing error state', async () => {
  server.use(http.get('/api/v1/graduates', () => HttpResponse.json([
    { ...graduates[0], dcf_assumptions: { ...dcfSettings, projection_years: '5\n' } },
  ])))
  renderWithClient(<GraduatesPanel />)
  expect(await screen.findByRole('alert')).toHaveTextContent(/could not load graduates/i)
  expect(screen.queryByText('DCF settings not recorded')).not.toBeInTheDocument()
  expect(screen.queryByText('70%')).not.toBeInTheDocument()
})

test('discloses small nonzero and subnormal recorded rates without rounding them to zero', async () => {
  server.use(http.get('/api/v1/graduates', () => HttpResponse.json([
    { ...graduates[0], dcf_assumptions: {
      ...dcfSettings, discount_rate: 1e-10, terminal_growth: -1e-10,
      min_growth: Number.MIN_VALUE, max_growth: 0,
    } },
  ])))
  renderWithClient(<GraduatesPanel />)
  const summary = await screen.findByText('Recorded DCF settings')
  await userEvent.click(summary)
  const details = summary.closest('details')!
  const formatter = new Intl.NumberFormat('en-US', { style: 'percent', maximumSignificantDigits: 6 })
  for (const rate of [1e-10, -1e-10, Number.MIN_VALUE]) {
    const formatted = formatter.format(rate)
    expect(formatted).not.toBe(formatter.format(0))
    expect(within(details).getByText(formatted)).toBeVisible()
  }
  expect(within(details).getByText('0%')).toBeVisible()
})

test('rejects undeclared present DCF settings through the existing error state', async () => {
  server.use(http.get('/api/v1/graduates', () => HttpResponse.json([
    { ...graduates[0], dcf_assumptions: { ...dcfSettings, guessed_growth: 0.1 } },
  ])))
  renderWithClient(<GraduatesPanel />)
  expect(await screen.findByRole('alert')).toHaveTextContent(/could not load graduates/i)
  expect(screen.queryByText('DCF settings not recorded')).not.toBeInTheDocument()
  expect(screen.queryByText('Recorded DCF settings')).not.toBeInTheDocument()
})
