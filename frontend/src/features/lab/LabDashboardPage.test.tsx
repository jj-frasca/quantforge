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
      forward_bars: 2,
      forward_return: 0.08,
      forward_sharpe: 0.9,
      buy_and_hold_return: -0.146,
      buy_and_hold_sharpe: -0.4,
      beats_buy_and_hold: true,
      as_of: '2026-07-08T00:00:00Z',
      forward_equity: [
        { timestamp: '2026-07-07T00:00:00Z', strategy_equity: 1.02, buy_and_hold_equity: 0.99 },
        { timestamp: '2026-07-08T00:00:00Z', strategy_equity: 1.08, buy_and_hold_equity: 0.854 },
      ],
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
  // The real forward equity curve renders once ≥2 forward bars have accrued (ADR-023).
  expect(screen.getByLabelText('equity curve CRM')).toBeInTheDocument()
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

const poolReport = {
  n_experiments: 3208,
  n_symbols: 607,
  n_trials: 115009,
  n_graduate_experiments: 206,
  n_leaderboard_graduates: 40,
  n_surviving_deflation: 0,
  near_misses: [],
  n_open_positions: 21,
  book: {
    n_survivors: 0,
    n_non_survivors: 0,
    n_unknown: 21,
    survivor_mean_forward_sharpe: null,
    non_survivor_mean_forward_sharpe: null,
  },
}

test('leads the dashboard with the universe-deflation headline (ADR-033)', async () => {
  server.use(
    http.get('/api/v1/leaderboard', () => HttpResponse.json(leaderboardRows)),
    http.get('/api/v1/paper-portfolio', () => HttpResponse.json(positions)),
    http.get('/api/v1/pool-report', () => HttpResponse.json(poolReport)),
  )
  renderWithClient(<LabDashboardPage />)

  expect(await screen.findByTestId('deflation-survivors')).toHaveTextContent('0 of 40')
  expect(screen.getByRole('status')).toHaveTextContent(/not distinguishable from selection luck/i)
})

test('the dashboard still renders when the pool report is unavailable', async () => {
  // The headline is a summary, not a precondition — a failing report must not take the page down.
  server.use(
    http.get('/api/v1/leaderboard', () => HttpResponse.json(leaderboardRows)),
    http.get('/api/v1/paper-portfolio', () => HttpResponse.json(positions)),
    http.get('/api/v1/pool-report', () => new HttpResponse(null, { status: 500 })),
  )
  renderWithClient(<LabDashboardPage />)

  expect(await screen.findByLabelText('leaderboard')).toBeInTheDocument()
  expect(screen.queryByTestId('deflation-survivors')).toBeNull()
})

test('surfaces the measured false-graduation rate alongside the headline (ADR-036/037)', async () => {
  server.use(
    http.get('/api/v1/leaderboard', () => HttpResponse.json(leaderboardRows)),
    http.get('/api/v1/paper-portfolio', () => HttpResponse.json(positions)),
    http.get('/api/v1/pool-report', () => HttpResponse.json(poolReport)),
    http.get('/api/v1/null-calibration', () =>
      HttpResponse.json([
        {
          n_symbols: 200,
          n_graduates: 2,
          false_graduation_rate: 0.01,
          n_clear_deflation_bar: 0,
          deflation_bar: 2.11,
          max_deflated_sharpe: 0.92,
          max_holdout_sharpe: 0.85,
          holdout_years: [2.4],
          walk_forward_oos_sharpes: [],
          purged_cv_oos_sharpes: [],
          gate_config_version: 'v1',
          null_mode: 'iid_normal',
        },
      ]),
    ),
  )
  renderWithClient(<LabDashboardPage />)

  expect(await screen.findByLabelText('gate calibration')).toBeInTheDocument()
  expect(screen.getByText('1.00%')).toBeInTheDocument()
})

test('the dashboard still renders when the gate has never been calibrated', async () => {
  server.use(
    http.get('/api/v1/leaderboard', () => HttpResponse.json(leaderboardRows)),
    http.get('/api/v1/paper-portfolio', () => HttpResponse.json(positions)),
    http.get('/api/v1/pool-report', () => HttpResponse.json(poolReport)),
    http.get('/api/v1/null-calibration', () => HttpResponse.json([])),
  )
  renderWithClient(<LabDashboardPage />)

  expect(await screen.findByLabelText('leaderboard')).toBeInTheDocument()
  expect(screen.queryByLabelText('gate calibration')).toBeNull()
})

test('leads with how the pool reads against a no-edge surrogate', async () => {
  server.use(
    http.get('/api/v1/leaderboard', () => HttpResponse.json([])),
    http.get('/api/v1/paper-portfolio', () => HttpResponse.json([])),
    http.get('/api/v1/null-comparison', () =>
      HttpResponse.json([
        {
          statistic: 'walk-forward',
          null_mode: 'bootstrap:SPY',
          real_n: 2427,
          real_median: 0.542,
          null_n: 200,
          null_median: 0.652,
          null_p95: 0.983,
          real_exceeds_null_p95: false,
          comparable: true,
          mismatch: '',
          matched_n: 2427,
          matched_n_bars: 5445,
        },
      ]),
    ),
  )
  renderWithClient(<LabDashboardPage />)

  expect(await screen.findByLabelText('null comparison')).toBeInTheDocument()
  expect(screen.getByText(/does not separate/i)).toBeInTheDocument()
})
