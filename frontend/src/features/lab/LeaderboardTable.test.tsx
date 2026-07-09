import { render, screen } from '@testing-library/react'

import type { LeaderboardRow } from '../../types/lab'
import { LeaderboardTable } from './LeaderboardTable'

const graduate: LeaderboardRow = {
  symbol: 'CRM',
  strategy_name: 'trend_filtered_mean_reversion',
  deflated_sharpe: 0.28,
  graduated: true,
  holdout_sharpe: 0.44,
  survives_universe_deflation: false,
}

const reject: LeaderboardRow = {
  symbol: 'SPY',
  strategy_name: 'donchian_breakout',
  deflated_sharpe: -0.12,
  graduated: false,
  holdout_sharpe: null,
  survives_universe_deflation: null,
}

test('renders a row per strategy with symbol, strategy and deflated Sharpe', () => {
  render(<LeaderboardTable rows={[graduate, reject]} />)
  expect(screen.getByRole('cell', { name: 'CRM' })).toBeInTheDocument()
  expect(screen.getByRole('cell', { name: 'trend_filtered_mean_reversion' })).toBeInTheDocument()
  expect(screen.getByRole('cell', { name: '0.28' })).toBeInTheDocument()
})

test('summarizes the tested count and graduate count', () => {
  render(<LeaderboardTable rows={[graduate, reject]} />)
  expect(screen.getByText(/2 strategies tested/i)).toBeInTheDocument()
  expect(screen.getByText(/1 graduate\b/i)).toBeInTheDocument()
})

test('marks graduate rows and shows the deflation verdict honestly', () => {
  render(<LeaderboardTable rows={[graduate]} />)
  const gradRow = screen.getByRole('cell', { name: 'CRM' }).closest('tr')
  expect(gradRow).toHaveClass('graduated')
  // Graduated per-symbol but does NOT survive cross-symbol selection deflation.
  expect(screen.getByText('selection-lucky')).toBeInTheDocument()
  expect(screen.getByText('graduate')).toBeInTheDocument()
})

test('shows an em dash for null holdout / deflation on rejected rows', () => {
  render(<LeaderboardTable rows={[reject]} />)
  const rejectRow = screen.getByRole('cell', { name: 'SPY' }).closest('tr')
  expect(rejectRow).not.toHaveClass('graduated')
  expect(screen.getByText('rejected')).toBeInTheDocument()
  // holdout Sharpe + deflation both render em dashes for a non-graduate.
  expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(2)
})

test('renders an empty state when there are no rows', () => {
  render(<LeaderboardTable rows={[]} />)
  expect(screen.getByText(/no strategies in the leaderboard yet/i)).toBeInTheDocument()
})
