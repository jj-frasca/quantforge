// WindowComparisonPanel: what ADR-063's longer search window did to the finalist the search picks
// (ADR-074). The surrogate and the criterion are different statistics and must not read alike.
import { render, screen } from '@testing-library/react'

import type { WindowComparison, WindowExperiment } from '../../types/lab'
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

// ADR-077: ADR-076's frozen result is a spent pre-registration, not a live statistic. It is read at
// the Pocock two-look boundary rather than at 95%, over its own 200-symbol sample, and the panel
// has to say all three of those things or the band gets compared to the wrong thing.
const experiment = (overrides: Partial<WindowComparison> = {}): WindowExperiment => ({
  sample: Array.from({ length: 200 }, (_, i) => `SYM${i}`),
  criterion_alpha: 0.0294,
  criterion: comparison({
    excess_n: 200,
    excess_delta_median: -0.008,
    excess_delta_ci_low: -0.055,
    excess_delta_ci_high: 0.022,
    ...overrides,
  }),
  at_look_one_alpha: comparison({
    excess_n: 200,
    excess_delta_median: -0.008,
    excess_delta_ci_low: -0.053,
    excess_delta_ci_high: 0.016,
  }),
})

test('reports the frozen experiment at its own boundary, not at 95%', () => {
  render(<WindowComparisonPanel comparison={comparison()} experiment={experiment()} />)

  const frozen = screen.getByTestId('window-experiment')
  expect(frozen).toHaveTextContent('-0.008')
  expect(frozen).toHaveTextContent('[-0.055, +0.022]')
  expect(frozen).toHaveTextContent(/0\.0294/)
})

test('names the frozen sample size rather than the live one', () => {
  render(<WindowComparisonPanel comparison={comparison()} experiment={experiment()} />)
  expect(screen.getByTestId('window-experiment')).toHaveTextContent(/200/)
})

test('says the sequence is closed so nobody reads the null as an invitation to re-run', () => {
  render(<WindowComparisonPanel comparison={comparison()} experiment={experiment()} />)
  expect(screen.getByTestId('window-experiment')).toHaveTextContent(/closed/i)
})

test('carries the look-1 reading labelled as continuity, not as a second result', () => {
  render(<WindowComparisonPanel comparison={comparison()} experiment={experiment()} />)

  const frozen = screen.getByTestId('window-experiment')
  expect(frozen).toHaveTextContent('[-0.053, +0.016]')
  expect(frozen).toHaveTextContent(/continuity/i)
})

test('points the live not-measured row at the frozen experiment instead of dead-ending', () => {
  render(<WindowComparisonPanel comparison={comparison()} experiment={experiment()} />)
  expect(screen.getByTestId('excess-delta')).toHaveTextContent(/ADR-076/)
})

test('says the experiment has not been run when there is no artifact', () => {
  render(<WindowComparisonPanel comparison={comparison()} experiment={null} />)
  expect(screen.getByTestId('window-experiment')).toHaveTextContent(/has not been run/i)
})
