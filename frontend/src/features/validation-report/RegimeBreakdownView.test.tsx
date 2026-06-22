// RegimeBreakdownView: renders the per-regime metrics from the validation report
// and — when one regime carries the edge — names the fragility explicitly. The
// component is purely presentational; thresholds for the framing copy live here.
import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import type { RegimeBreakdownEntry } from '../../types/validation'
import { RegimeBreakdownView } from './RegimeBreakdownView'

const entry = (sharpe: number, totalReturn: number, nBars = 100): RegimeBreakdownEntry => ({
  sharpe,
  total_return: totalReturn,
  n_bars: nBars,
})

test('renders nothing when the breakdown is empty', () => {
  // Validation can return an empty regime_breakdown (e.g. extremely short window
  // collapses every bar into one bucket). Render nothing rather than a misleading
  // empty table.
  const { container } = render(<RegimeBreakdownView breakdown={{}} />)
  expect(container.firstChild).toBeNull()
})

test('renders one row per regime with sharpe + total return + bar count', () => {
  render(
    <RegimeBreakdownView
      breakdown={{ bull: entry(1.1, 0.18, 220), bear: entry(0.2, 0.02, 80) }}
    />,
  )
  const region = screen.getByRole('region', { name: /regime breakdown/i })
  expect(region).toBeInTheDocument()
  // Each regime label is rendered.
  expect(region).toHaveTextContent(/bull/i)
  expect(region).toHaveTextContent(/bear/i)
  // Bar counts visible.
  expect(region).toHaveTextContent(/220/)
  expect(region).toHaveTextContent(/80/)
})

test('flags a "fragile in one regime" gap when Sharpe in one regime dwarfs the other', () => {
  // Methodology hook: when bull-Sharpe is materially higher than bear-Sharpe (or
  // vice versa), the strategy only has an edge in one regime and a regime change
  // could erase the performance. The component names that explicitly.
  render(
    <RegimeBreakdownView
      breakdown={{ bull: entry(1.4, 0.22, 200), bear: entry(0.05, 0.01, 100) }}
    />,
  )
  const region = screen.getByRole('region', { name: /regime breakdown/i })
  expect(region).toHaveTextContent(/only works in/i)
})

test('does NOT flag when the strategy is roughly balanced across regimes', () => {
  // A regime-robust strategy is the boring good case; no flag.
  render(
    <RegimeBreakdownView
      breakdown={{ bull: entry(0.9, 0.12, 200), bear: entry(0.8, 0.10, 100) }}
    />,
  )
  expect(screen.queryByText(/only works in/i)).not.toBeInTheDocument()
})

test('skips the fragility flag when only one regime has data', () => {
  // A single-regime breakdown means the analysis window never crossed a regime
  // boundary; we can't conclude anything about cross-regime fragility from one
  // bucket, so the flag is suppressed.
  render(<RegimeBreakdownView breakdown={{ bull: entry(1.2, 0.18, 200) }} />)
  expect(screen.queryByText(/only works in/i)).not.toBeInTheDocument()
})
