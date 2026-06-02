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

test('renders the chart container when a benchmark curve is provided', () => {
  // (Recharts SVG + legend aren't asserted — jsdom doesn't paint dimensions; we cover
  // the no-crash + summary path. The benchmark line proves itself in the browser.)
  const bench: EquityPoint[] = [
    { timestamp_utc: '2024-01-01T00:00:00Z', equity: 100_000 },
    { timestamp_utc: '2024-12-01T00:00:00Z', equity: 108_000 },
  ]
  render(<EquityCurveChart data={curve} benchmark={bench} benchmarkLabel="Buy & hold AAPL" />)
  expect(screen.getByLabelText('equity curve')).toBeInTheDocument()
  expect(screen.getByText(/Ending equity \$112,000/)).toBeInTheDocument()
})

test('renders an empty-state message when the curve is empty', () => {
  render(<EquityCurveChart data={[]} />)
  expect(screen.getByText(/no equity points/i)).toBeInTheDocument()
})
