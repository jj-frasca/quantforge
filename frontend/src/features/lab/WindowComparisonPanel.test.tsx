// WindowComparisonPanel: what ADR-063's longer search window did to the finalist the search picks
// (ADR-074). The surrogate and the criterion are different statistics and must not read alike.
import { render, screen } from '@testing-library/react'

import type { WindowComparison } from '../../types/lab'
import { WindowComparisonPanel } from './WindowComparisonPanel'

const comparison = (overrides: Partial<WindowComparison> = {}): WindowComparison => ({
  n_symbols: 368,
  short_n_bars: 5446,
  long_n_bars: 9232,
  oos_delta_median: -0.038,
  oos_delta_ci_low: -0.06,
  oos_delta_ci_high: -0.009,
  in_sample_delta_median: 0.012,
  in_sample_delta_ci_low: -0.005,
  in_sample_delta_ci_high: 0.034,
  n_finalist_changed: 257,
  excess_n: 0,
  excess_delta_median: null,
  excess_delta_ci_low: null,
  excess_delta_ci_high: null,
  ...overrides,
})

test('reports each delta with the interval it was measured to', () => {
  render(<WindowComparisonPanel comparison={comparison()} />)

  expect(screen.getByText('-0.038')).toBeInTheDocument()
  expect(screen.getByText('[-0.060, -0.009]')).toBeInTheDocument()
  expect(screen.getByText('+0.012')).toBeInTheDocument()
  expect(screen.getByText('[-0.005, +0.034]')).toBeInTheDocument()
})

test('labels the raw delta a surrogate rather than the verdict', () => {
  render(<WindowComparisonPanel comparison={comparison()} />)
  expect(screen.getByText(/surrogate/i)).toBeInTheDocument()
})

test('says the drift-controlled delta is not measured rather than showing a zero', () => {
  render(<WindowComparisonPanel comparison={comparison()} />)

  expect(screen.getByTestId('excess-delta')).toHaveTextContent(/not measured/i)
  expect(screen.queryByText('+0.000')).not.toBeInTheDocument()
})

test('shows the drift-controlled delta once both windows carry the benchmark', () => {
  render(
    <WindowComparisonPanel
      comparison={comparison({
        excess_n: 45,
        excess_delta_median: -0.074,
        excess_delta_ci_low: -0.157,
        excess_delta_ci_high: 0.03,
      })}
    />,
  )

  expect(screen.getByTestId('excess-delta')).toHaveTextContent('-0.074')
  expect(screen.getByTestId('excess-delta')).toHaveTextContent('[-0.157, +0.030]')
  expect(screen.queryByText(/not measured/i)).not.toBeInTheDocument()
})

test('says how often the longer window changed which strategy the search picks', () => {
  render(<WindowComparisonPanel comparison={comparison()} />)
  expect(screen.getByText(/257 of 368/)).toBeInTheDocument()
})

test('reports the two window lengths it paired across', () => {
  render(<WindowComparisonPanel comparison={comparison()} />)
  expect(screen.getByText(/5,446/)).toBeInTheDocument()
  expect(screen.getByText(/9,232/)).toBeInTheDocument()
})
