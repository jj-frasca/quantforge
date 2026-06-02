// PriceChart: summary text + chart container for non-empty bars; explicit empty-state
// message when no bars are cached. (Recharts SVG geometry isn't asserted — jsdom
// doesn't paint dimensions; we cover the user-visible chrome instead.)
import { render, screen } from '@testing-library/react'

import type { BarsResponse } from '../../types/bars'
import { PriceChart } from './PriceChart'

const populated: BarsResponse = {
  symbol: 'AAPL',
  n_bars: 2,
  bars: [
    {
      timestamp_utc: '2024-01-01T00:00:00Z',
      open: 100,
      high: 101,
      low: 99,
      close: 100.5,
      volume: 1_000_000,
    },
    {
      timestamp_utc: '2024-01-02T00:00:00Z',
      open: 100.5,
      high: 102,
      low: 100,
      close: 101.75,
      volume: 1_100_000,
    },
  ],
}

const empty: BarsResponse = { symbol: 'AAPL', n_bars: 0, bars: [] }

test('renders the summary text and the chart container for populated bars', () => {
  render(<PriceChart data={populated} />)
  expect(screen.getByLabelText('price chart')).toBeInTheDocument()
  expect(screen.getByText(/2 bars/)).toBeInTheDocument()
  expect(screen.getByText(/last close 101\.75/)).toBeInTheDocument()
})

test('renders the empty-state message when no bars are cached', () => {
  render(<PriceChart data={empty} />)
  expect(screen.getByText(/no cached bars/i)).toBeInTheDocument()
})
