// ForwardComparisonChart: summary text is asserted; the Recharts SVG isn't painted by jsdom
// (same convention as EquityCurveChart) — we cover the summary + empty-state paths.
import { render, screen } from '@testing-library/react'

import type { PaperPosition } from '../../types/lab'
import { ForwardComparisonChart } from './ForwardComparisonChart'

const scored: PaperPosition = {
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
    as_of: '2026-07-08T00:00:00Z',
    forward_equity: [],
  },
}

const scoredLosing: PaperPosition = {
  ...scored,
  symbol: 'LOW',
  score: { ...scored.score!, forward_sharpe: -0.2, buy_and_hold_sharpe: 0.5, beats_buy_and_hold: false },
}

const unscored: PaperPosition = {
  symbol: 'AAPL',
  strategy_name: 'sma',
  parameters: {},
  frozen_at: '2026-07-06T00:00:00Z',
  status: 'open',
  exit_reasons: [],
  score: null,
}

test('summarizes how many scored positions beat buy-and-hold', () => {
  render(<ForwardComparisonChart positions={[scored, scoredLosing]} />)
  expect(screen.getByLabelText('forward vs buy-and-hold')).toBeInTheDocument()
  expect(screen.getByText(/1 of 2 positions beating buy-and-hold/i)).toBeInTheDocument()
})

test('ignores positions without a forward score', () => {
  render(<ForwardComparisonChart positions={[scored, unscored]} />)
  // Only the one scored position counts toward the denominator.
  expect(screen.getByText(/1 of 1 position beating buy-and-hold/i)).toBeInTheDocument()
})

test('renders an empty state when no position has a score', () => {
  render(<ForwardComparisonChart positions={[unscored]} />)
  expect(screen.getByText(/no forward scores yet/i)).toBeInTheDocument()
})
