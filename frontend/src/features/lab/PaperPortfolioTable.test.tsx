import { render, screen } from '@testing-library/react'

import type { PaperPosition } from '../../types/lab'
import { PaperPortfolioTable } from './PaperPortfolioTable'

const open: PaperPosition = {
  symbol: 'CRM',
  strategy_name: 'trend_filtered_mean_reversion',
  parameters: { window: 20 },
  frozen_at: '2026-07-06T00:00:00Z',
  status: 'open',
  exit_reasons: [],
  score: {
    forward_bars: 42,
    forward_return: 0.08,
    forward_sharpe: 0.9,
    buy_and_hold_return: -0.146,
    buy_and_hold_sharpe: -0.4,
    beats_buy_and_hold: true,
    forward_trades: 7,
    as_of: '2026-07-08T00:00:00Z',
    forward_equity: [],
  },
}

const closed: PaperPosition = {
  symbol: 'LOW',
  strategy_name: 'rsi_mean_reversion',
  parameters: { period: 14 },
  frozen_at: '2026-07-06T00:00:00Z',
  status: 'closed',
  closed_at: '2026-08-01T00:00:00Z',
  exit_reasons: ['rolling Sharpe -0.10 <= 0.0 (edge has decayed)'],
  score: null,
}

test('renders a row per position with symbol, strategy and forward Sharpe', () => {
  render(<PaperPortfolioTable positions={[open]} />)
  expect(screen.getByRole('cell', { name: 'CRM' })).toBeInTheDocument()
  expect(screen.getByRole('cell', { name: 'trend_filtered_mean_reversion' })).toBeInTheDocument()
  expect(screen.getByRole('cell', { name: '0.90' })).toBeInTheDocument()
  expect(screen.getByText(/42 forward bars/i)).toBeInTheDocument()
})

test('renders a position that has never traded as unmeasured, not as a score of zero', () => {
  // ADR-073: an all-zero forward series has Sharpe 0.0 by the degenerate-series guard. The table
  // used to render that as a real 0.00 next to a "beats" colour, which is how 18 of the book's
  // closed positions looked healthy right up until they were cut for a decayed edge they never had.
  const untraded: PaperPosition = {
    ...open,
    score: {
      ...open.score!,
      forward_bars: 21,
      forward_trades: 0,
      forward_return: 0,
      forward_sharpe: 0,
      beats_buy_and_hold: false,
    },
  }
  render(<PaperPortfolioTable positions={[untraded]} />)
  expect(screen.getByText(/not yet measurable — 0 trades in 21 forward bars/i)).toBeInTheDocument()
  expect(screen.queryByRole('cell', { name: '0.00' })).not.toBeInTheDocument()
})

test('summarizes the position count and open count', () => {
  render(<PaperPortfolioTable positions={[open, closed]} />)
  expect(screen.getByText(/2 positions · 1 open/i)).toBeInTheDocument()
})

test('styles open vs closed positions differently and shows the status badge', () => {
  render(<PaperPortfolioTable positions={[open, closed]} />)
  const openRow = screen.getByRole('cell', { name: 'CRM' }).closest('tr')
  const closedRow = screen.getByRole('cell', { name: 'LOW' }).closest('tr')
  expect(openRow).toHaveClass('open')
  expect(closedRow).toHaveClass('closed')
  expect(screen.getByText('open')).toBeInTheDocument()
  expect(screen.getByText('closed')).toBeInTheDocument()
})

test('lists exit reasons for a closed position', () => {
  render(<PaperPortfolioTable positions={[closed]} />)
  expect(screen.getByText(/edge has decayed/i)).toBeInTheDocument()
})

test('shows a "no forward data yet" note when an open position has no score', () => {
  render(<PaperPortfolioTable positions={[{ ...open, score: null }]} />)
  expect(screen.getByText(/no forward data yet/i)).toBeInTheDocument()
})

test('renders an empty state when there are no positions', () => {
  render(<PaperPortfolioTable positions={[]} />)
  expect(screen.getByText(/no paper positions yet/i)).toBeInTheDocument()
})
