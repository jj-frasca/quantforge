// EquityCurveChart: summary text shows ending equity + total return %; empty state
// renders a "run a backtest" prompt (Recharts SVG isn't asserted — see PriceChart).
import { render, screen } from '@testing-library/react'

import type { EquityPoint } from '../../types/backtest'
import { EquityCurveChart } from './EquityCurveChart'

const curve: EquityPoint[] = [
  { timestamp_utc: '2024-01-01T00:00:00Z', equity: 100_000 },
  { timestamp_utc: '2024-06-01T00:00:00Z', equity: 105_000 },
  { timestamp_utc: '2024-12-01T00:00:00Z', equity: 112_000 },
]

test('renders the ending equity and percent change for a populated curve', () => {
  render(<EquityCurveChart data={curve} />)
  expect(screen.getByLabelText('equity curve')).toBeInTheDocument()
  expect(screen.getByText(/Ending equity \$112,000/)).toBeInTheDocument()
  expect(screen.getByText(/12\.0%/)).toBeInTheDocument()
})

test('renders an empty-state message when the curve is empty', () => {
  render(<EquityCurveChart data={[]} />)
  expect(screen.getByText(/no equity points/i)).toBeInTheDocument()
})
