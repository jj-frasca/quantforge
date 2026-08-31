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
  null_p5: 0.22,
  real_exceeds_null_p95: false,
  real_below_null_p5: false,
  difference_ci_low: null,
  difference_ci_high: null,
  difference_n_clusters: 0,
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
  expect(screen.getByTestId('excess-note-walk-forward excess')).toHaveTextContent(/not measured/i)
  expect(screen.getByTestId('excess-note-purged-CV excess')).toHaveTextContent(/not measured/i)
})

test('renders the excess row as its own statistic once both sides carry it', () => {
  render(
    <NullComparisonPanel
      comparisons={[row(), row({ statistic: 'walk-forward excess', real_median: -0.004, null_median: -0.006, null_p95: 0.096 })]}
    />,
  )

  expect(screen.getByText('walk-forward excess')).toBeInTheDocument()
  expect(screen.getByText('-0.004')).toBeInTheDocument()
  expect(screen.queryByTestId('excess-note-walk-forward excess')).not.toBeInTheDocument()
})

test('renders nothing when nothing has been compared', () => {
  const { container } = render(<NullComparisonPanel comparisons={[]} />)
  expect(container).toBeEmptyDOMElement()
})

// --- ADR-072: the centered row is read two-sided ---

test('reports the null band lower edge beside its upper one', () => {
  render(<NullComparisonPanel comparisons={[row()]} />)
  expect(screen.getByText('+0.220')).toBeInTheDocument()
  expect(screen.getByText('+0.983')).toBeInTheDocument()
})

test('an excess row under the null band says the search subtracts', () => {
  render(
    <NullComparisonPanel
      comparisons={[
        row({
          statistic: 'walk-forward excess',
          real_median: -0.4,
          null_median: -0.006,
          null_p5: -0.233,
          null_p95: 0.096,
          real_below_null_p5: true,
        }),
      ]}
    />,
  )

  expect(screen.getByText(/separates below/i)).toBeInTheDocument()
  expect(screen.queryByText(/does not separate/i)).not.toBeInTheDocument()
})

test('an excess row inside the band still reads as neutral', () => {
  render(
    <NullComparisonPanel
      comparisons={[
        row({
          statistic: 'walk-forward excess',
          real_median: -0.125,
          null_median: -0.006,
          null_p5: -0.233,
          null_p95: 0.096,
        }),
      ]}
    />,
  )

  expect(screen.getByText(/does not separate/i)).toBeInTheDocument()
  expect(screen.queryByText(/separates below/i)).not.toBeInTheDocument()
})

// --- ADR-075: the difference of medians, sized by a symbol-clustered bootstrap ---

const excessRow = (overrides: Partial<NullComparison> = {}): NullComparison =>
  row({
    statistic: 'walk-forward excess',
    real_median: -0.125,
    null_median: -0.006,
    null_p5: -0.233,
    null_p95: 0.096,
    difference_ci_low: -0.215,
    difference_ci_high: -0.061,
    difference_n_clusters: 66,
    ...overrides,
  })

test('reports the clustered difference beside the verdict, not instead of it', () => {
  render(<NullComparisonPanel comparisons={[excessRow()]} />)

  expect(screen.getByText(/does not separate/i)).toBeInTheDocument()
  expect(screen.getByTestId('difference-interval')).toHaveTextContent('-0.119')
  expect(screen.getByTestId('difference-interval')).toHaveTextContent('[-0.215, -0.061]')
  expect(screen.getByTestId('difference-interval')).toHaveTextContent(/66 symbol clusters/i)
})

test('says when the clustered interval excludes zero', () => {
  render(<NullComparisonPanel comparisons={[excessRow()]} />)
  expect(screen.getByTestId('difference-interval')).toHaveTextContent(/excludes zero/i)
})

test('says when the clustered interval spans zero', () => {
  render(
    <NullComparisonPanel
      comparisons={[excessRow({ difference_ci_low: -0.2, difference_ci_high: 0.05 })]}
    />,
  )
  expect(screen.getByTestId('difference-interval')).toHaveTextContent(/spans zero/i)
})

test('never hides that the interval is a lower bound on its own width', () => {
  render(<NullComparisonPanel comparisons={[excessRow()]} />)
  expect(screen.getByTestId('difference-interval')).toHaveTextContent(/lower bound/i)
})

test('a row with no clustered interval shows none', () => {
  render(<NullComparisonPanel comparisons={[row()]} />)
  expect(screen.queryByTestId('difference-interval')).not.toBeInTheDocument()
})

test('a refused row never renders a clustered significance interval', () => {
  render(
    <NullComparisonPanel
      comparisons={[
        excessRow({
          comparable: false,
          mismatch: 'only 3 matched diagnostics measured (need 30 to measure a median)',
        }),
      ]}
    />,
  )

  expect(screen.getByText(/not comparable/i)).toBeInTheDocument()
  expect(screen.queryByTestId('difference-interval')).not.toBeInTheDocument()
})

test('an interval below the minimum symbol-cluster sample is not rendered', () => {
  render(<NullComparisonPanel comparisons={[excessRow({ difference_n_clusters: 1 })]} />)

  expect(screen.queryByTestId('difference-interval')).not.toBeInTheDocument()
})

// --- ADR-078: a second drift-controlled row, and the two must be told apart ---

test('names each missing control separately rather than hiding one behind the other', () => {
  render(
    <NullComparisonPanel
      comparisons={[
        row(),
        row({ statistic: 'purged-CV' }),
        row({ statistic: 'walk-forward excess', real_median: -0.127 }),
      ]}
    />,
  )

  // The walk-forward control exists, so only the purged-CV one is outstanding. Before ADR-078 a
  // single `hasExcess` flag suppressed the whole note as soon as EITHER control landed, which
  // silently told the reader the purged-CV row was drift-controlled when it was not (ADR-067).
  expect(screen.getByTestId('excess-note-purged-CV excess')).toHaveTextContent(/not measured/i)
  expect(screen.queryByTestId('excess-note-walk-forward excess')).not.toBeInTheDocument()
})

test('drops both notes once both controls are measured', () => {
  render(
    <NullComparisonPanel
      comparisons={[
        row({ statistic: 'walk-forward excess', real_median: -0.127 }),
        row({ statistic: 'purged-CV excess', real_median: -0.09 }),
      ]}
    />,
  )

  expect(screen.queryByTestId('excess-note-walk-forward excess')).not.toBeInTheDocument()
  expect(screen.queryByTestId('excess-note-purged-CV excess')).not.toBeInTheDocument()
  expect(screen.getByText('purged-CV excess')).toBeInTheDocument()
})

test('a difference interval says which statistic it belongs to', () => {
  render(
    <NullComparisonPanel
      comparisons={[
        excessRow(),
        excessRow({
          statistic: 'purged-CV excess',
          real_median: -0.09,
          difference_ci_low: -0.18,
          difference_ci_high: -0.02,
        }),
      ]}
    />,
  )

  // Two intervals, same null mode, different statistics — without the label they are two
  // identically-headed paragraphs of different numbers.
  const intervals = screen.getAllByTestId('difference-interval')
  expect(intervals).toHaveLength(2)
  expect(intervals[0]).toHaveTextContent('walk-forward excess')
  expect(intervals[1]).toHaveTextContent('purged-CV excess')
})
