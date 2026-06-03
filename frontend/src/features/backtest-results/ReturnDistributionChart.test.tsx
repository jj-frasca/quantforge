// ReturnDistributionChart: summary text with skew + excess kurtosis; empty state for
// zero bins. Recharts SVG itself not asserted (same jsdom limitation as other charts).
import { render, screen } from '@testing-library/react'

import type { ReturnDistribution } from '../../types/backtest'
import { ReturnDistributionChart } from './ReturnDistributionChart'

const populated: ReturnDistribution = {
  bins: [
    { bin_center: -0.02, frequency: 5 },
    { bin_center: 0, frequency: 80 },
    { bin_center: 0.02, frequency: 15 },
  ],
  skewness: -0.42,
  kurtosis: 1.85,
}

test('renders skew + excess kurtosis in the summary line', () => {
  render(<ReturnDistributionChart data={populated} />)
  expect(screen.getByLabelText('return distribution')).toBeInTheDocument()
  expect(screen.getByText(/skew -0\.42/)).toBeInTheDocument()
  expect(screen.getByText(/excess kurtosis 1\.85/)).toBeInTheDocument()
})

test('renders an empty-state message when there are no bins', () => {
  render(
    <ReturnDistributionChart data={{ bins: [], skewness: 0, kurtosis: 0 }} />,
  )
  expect(screen.getByText(/no returns to bin/i)).toBeInTheDocument()
})
