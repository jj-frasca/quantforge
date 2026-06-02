// DrawdownChart: max drawdown summary; empty state. (Recharts SVG not asserted.)
import { render, screen } from '@testing-library/react'

import type { DrawdownPoint } from '../../types/backtest'
import { DrawdownChart } from './DrawdownChart'

const curve: DrawdownPoint[] = [
  { timestamp_utc: '2024-01-01T00:00:00Z', drawdown: 0 },
  { timestamp_utc: '2024-06-01T00:00:00Z', drawdown: -0.05 },
  { timestamp_utc: '2024-09-01T00:00:00Z', drawdown: -0.18 },
  { timestamp_utc: '2024-12-01T00:00:00Z', drawdown: -0.02 },
]

test('renders the worst drawdown for a populated curve', () => {
  render(<DrawdownChart data={curve} />)
  expect(screen.getByLabelText('drawdown')).toBeInTheDocument()
  expect(screen.getByText(/max drawdown -18\.0%/i)).toBeInTheDocument()
})

test('renders an empty-state message when no drawdown points', () => {
  render(<DrawdownChart data={[]} />)
  expect(screen.getByText(/no drawdown points/i)).toBeInTheDocument()
})
