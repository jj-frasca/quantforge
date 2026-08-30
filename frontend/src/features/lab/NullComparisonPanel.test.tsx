// NullComparisonPanel: how the pool's out-of-sample diagnostics read against a surrogate with no
// edge by construction (ADR-051/064/068) — the claim the rest of the dashboard is judged against.
import { render, screen } from '@testing-library/react'

import type { NullComparison } from '../../types/lab'
import { NullComparisonPanel } from './NullComparisonPanel'

const row = (overrides: Partial<NullComparison> = {}): NullComparison => ({
  statistic: 'walk-forward',
  null_mode: 'bootstrap:SPY',
  real_n: 2427,
  real_median: 0.542,
  null_n: 200,
  null_median: 0.652,
  null_p95: 0.983,
  real_exceeds_null_p95: false,
  comparable: true,
  mismatch: '',
  matched_n: 2427,
  matched_n_bars: 5445,
  ...overrides,
})

test('states the verdict for each statistic and null mode', () => {
  render(<NullComparisonPanel comparisons={[row(), row({ null_mode: 'iid_normal' })]} />)

  expect(screen.getByText('bootstrap:SPY')).toBeInTheDocument()
  expect(screen.getByText('iid_normal')).toBeInTheDocument()
  expect(screen.getAllByText(/does not separate/i)).toHaveLength(2)
  expect(screen.getAllByText('+0.542')).toHaveLength(2)
})

test('a row that separates says so rather than being read off the numbers', () => {
  render(<NullComparisonPanel comparisons={[row({ real_median: 1.2, real_exceeds_null_p95: true })]} />)
  expect(screen.getByText(/separates/i)).toBeInTheDocument()
  expect(screen.queryByText(/does not separate/i)).not.toBeInTheDocument()
})

test('a row that cannot be compared shows why instead of a verdict', () => {
  render(
    <NullComparisonPanel
      comparisons={[
        row({ comparable: false, mismatch: "no experiment's history is within 10% of 7400 bars" }),
      ]}
    />,
  )

  expect(screen.getByText(/not comparable/i)).toBeInTheDocument()
  expect(screen.getByText(/within 10% of 7400 bars/)).toBeInTheDocument()
  expect(screen.queryByText(/does not separate/i)).not.toBeInTheDocument()
})

test('shows the matched sample the real median was taken over', () => {
  render(<NullComparisonPanel comparisons={[row()]} />)
  expect(screen.getByText('2,427 @ 5,445 bars')).toBeInTheDocument()
})

test('says the drift-controlled comparison is not measured when no excess row exists', () => {
  render(<NullComparisonPanel comparisons={[row()]} />)
  expect(screen.getByTestId('excess-note')).toHaveTextContent(/not measured/i)
})

test('renders the excess row as its own statistic once both sides carry it', () => {
  render(
    <NullComparisonPanel
      comparisons={[row(), row({ statistic: 'walk-forward excess', real_median: -0.004, null_median: -0.006, null_p95: 0.096 })]}
    />,
  )

  expect(screen.getByText('walk-forward excess')).toBeInTheDocument()
  expect(screen.getByText('-0.004')).toBeInTheDocument()
  expect(screen.queryByTestId('excess-note')).not.toBeInTheDocument()
})

test('renders nothing when nothing has been compared', () => {
  const { container } = render(<NullComparisonPanel comparisons={[]} />)
  expect(container).toBeEmptyDOMElement()
})
