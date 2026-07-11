// PositionEquityCurve: summary text is asserted; the Recharts SVG isn't painted by jsdom (same
// convention as EquityCurveChart). Covers the render, the <2-point null guard, and the summary math.
import { render, screen } from '@testing-library/react'

import type { PaperPosition } from '../../types/lab'
import { PositionEquityCurve } from './PositionEquityCurve'

const base: PaperPosition = {
  symbol: 'CRM',
  strategy_name: 'trend_filtered_mean_reversion',
  parameters: { window: 20 },
  frozen_at: '2026-07-06T00:00:00Z',
  status: 'open',
  exit_reasons: [],
  score: {
    forward_bars: 3,
    forward_return: 0.08,
    forward_sharpe: 0.9,
    buy_and_hold_return: -0.146,
    buy_and_hold_sharpe: -0.4,
    beats_buy_and_hold: true,
    as_of: '2026-07-09T00:00:00Z',
    forward_equity: [
      { timestamp: '2026-07-07T00:00:00Z', strategy_equity: 1.01, buy_and_hold_equity: 0.99 },
      { timestamp: '2026-07-08T00:00:00Z', strategy_equity: 1.05, buy_and_hold_equity: 0.92 },
      { timestamp: '2026-07-09T00:00:00Z', strategy_equity: 1.08, buy_and_hold_equity: 0.854 },
    ],
  },
}

test('renders the curve with a forward-vs-buy-and-hold summary', () => {
  render(<PositionEquityCurve position={base} />)
  expect(screen.getByLabelText('equity curve CRM')).toBeInTheDocument()
  // 1.08 index -> +8.0% forward; 0.854 index -> -14.6% buy-and-hold.
  expect(screen.getByText(/forward 8\.0% vs buy-and-hold -14\.6%/i)).toBeInTheDocument()
})

test('renders nothing when fewer than two forward points have accrued', () => {
  const oneBar: PaperPosition = {
    ...base,
    score: { ...base.score!, forward_equity: [base.score!.forward_equity[0]] },
  }
  const { container } = render(<PositionEquityCurve position={oneBar} />)
  expect(container).toBeEmptyDOMElement()
})

test('renders nothing when the position has no score', () => {
  const { container } = render(<PositionEquityCurve position={{ ...base, score: null }} />)
  expect(container).toBeEmptyDOMElement()
})
