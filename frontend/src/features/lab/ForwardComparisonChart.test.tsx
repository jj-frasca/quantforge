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
    forward_trades: 7,
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

test('renders both bars when the same symbol holds two scored positions under different strategies', () => {
  // A symbol can legitimately appear twice: it graduated under one strategy, that position
  // retired, and it later re-graduated under a different one — both can carry a forward score
  // simultaneously (confirmed directly against data/paper_portfolio.json: BIIB, DLR, and IT
  // each hold two scored positions under different strategy_names). Every other list in this
  // feature (LeaderboardTable, GraduatesPanel, PaperPortfolioTable) keys by
  // `${symbol}-${strategy_name}`; this chart keyed its bars by bare `symbol` alone, so the second
  // position collided with the first as a React key.
  //
  // NOT verifiable here: a real Playwright run against this exact production data (e2e/smoke.spec.ts,
  // now covering the "Live" page) caught this live as a "two children with the same key" React
  // console.error; jsdom does not reproduce it — this test passes identically before and after
  // the fix (confirmed directly, not assumed) because Recharts' <Bar> reads its <Cell> children as
  // configuration via React.Children rather than mounting them through jsdom's DOM reconciler the
  // same way a real browser does. Same jsdom-blind-spot class as ADR-130's minus-sign input bug.
  // The summary count below is the one thing jsdom CAN verify: both positions are counted.
  const secondStrategy: PaperPosition = {
    ...scored,
    strategy_name: 'vwap_reversion',
    score: { ...scored.score!, forward_sharpe: 0.3, beats_buy_and_hold: true },
  }
  render(<ForwardComparisonChart positions={[scored, secondStrategy]} />)
  expect(screen.getByText(/2 of 2 positions beating buy-and-hold/i)).toBeInTheDocument()
})
