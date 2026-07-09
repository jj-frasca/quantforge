import { screen, waitForElementToBeRemoved } from '@testing-library/react'
import { http, HttpResponse } from 'msw'

import { server } from '../../test/server'
import { renderWithClient } from '../../test/utils'
import { LabDashboardPage } from './LabDashboardPage'

const leaderboardRows = [
  {
    symbol: 'CRM',
    strategy_name: 'trend_filtered_mean_reversion',
    deflated_sharpe: 0.28,
    graduated: true,
    holdout_sharpe: 0.44,
    survives_universe_deflation: false,
  },
]

const positions = [
  {
    symbol: 'CRM',
    strategy_name: 'trend_filtered_mean_reversion',
    parameters: { window: 20 },
    frozen_at: '2026-07-06T00:00:00Z',
    status: 'open',
    closed_at: null,
    exit_reasons: [],
    score: {
      forward_bars: 42,
      forward_return: 0.08,
      forward_sharpe: 0.9,
      buy_and_hold_return: -0.146,
      buy_and_hold_sharpe: -0.4,
      beats_buy_and_hold: true,
      as_of: '2026-07-08T00:00:00Z',
    },
  },
]

test('renders the leaderboard and paper portfolio from the endpoints', async () => {
  server.use(
    http.get('/api/v1/leaderboard', () => HttpResponse.json(leaderboardRows)),
    http.get('/api/v1/paper-portfolio', () => HttpResponse.json(positions)),
  )
  renderWithClient(<LabDashboardPage />)

  expect(await screen.findByLabelText('leaderboard')).toBeInTheDocument()
  expect(await screen.findByLabelText('paper portfolio')).toBeInTheDocument()
  // Both sections render the CRM position/row.
  expect(screen.getAllByRole('cell', { name: 'CRM' }).length).toBeGreaterThanOrEqual(2)
  expect(screen.getByText(/1 of 1 position beating buy-and-hold/i)).toBeInTheDocument()
})

test('renders empty states when both endpoints return no data', async () => {
  server.use(
    http.get('/api/v1/leaderboard', () => HttpResponse.json([])),
    http.get('/api/v1/paper-portfolio', () => HttpResponse.json([])),
  )
  renderWithClient(<LabDashboardPage />)

  expect(await screen.findByText(/no strategies in the leaderboard yet/i)).toBeInTheDocument()
  expect(screen.getByText(/no paper positions yet/i)).toBeInTheDocument()
})

test('shows an error message when the leaderboard endpoint fails', async () => {
  server.use(
    http.get('/api/v1/leaderboard', () => new HttpResponse(null, { status: 500 })),
    http.get('/api/v1/paper-portfolio', () => HttpResponse.json([])),
  )
  renderWithClient(<LabDashboardPage />)

  expect(await screen.findByText(/could not load the leaderboard/i)).toBeInTheDocument()
})

test('shows a loading indicator while the portfolio is pending', async () => {
  server.use(
    http.get('/api/v1/leaderboard', () => HttpResponse.json([])),
    http.get('/api/v1/paper-portfolio', () => HttpResponse.json(positions)),
  )
  renderWithClient(<LabDashboardPage />)

  // The pending status is shown first, then removed once data arrives.
  await waitForElementToBeRemoved(() => screen.queryByText(/loading paper portfolio/i))
  expect(await screen.findByLabelText('paper portfolio')).toBeInTheDocument()
})
