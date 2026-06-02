// RollingSharpeChart: summary text + container for non-empty; empty state for [].
import { render, screen } from '@testing-library/react'

import type { RollingSharpePoint } from '../../types/backtest'
import { RollingSharpeChart } from './RollingSharpeChart'

const curve: RollingSharpePoint[] = [
  { timestamp_utc: '2024-01-01T00:00:00Z', sharpe: 0 },
  { timestamp_utc: '2024-06-01T00:00:00Z', sharpe: 1.5 },
  { timestamp_utc: '2024-12-01T00:00:00Z', sharpe: 1.2 },
]

test('renders the summary with the window size for a populated curve', () => {
  render(<RollingSharpeChart data={curve} window={60} />)
  expect(screen.getByLabelText('rolling sharpe')).toBeInTheDocument()
  expect(screen.getByText(/60-bar window/i)).toBeInTheDocument()
})

test('renders an empty-state message when no points', () => {
  render(<RollingSharpeChart data={[]} window={60} />)
  expect(screen.getByText(/no rolling sharpe points/i)).toBeInTheDocument()
})
