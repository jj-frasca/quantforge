import { render, screen, within } from '@testing-library/react'

import type { PaperPosition } from '../../types/lab'
import { PaperPortfolioTable } from './PaperPortfolioTable'

const open: PaperPosition = {
  symbol: 'CRM',
  strategy_name: 'trend_filtered_mean_reversion',
  parameters: { window: 20 },
  frozen_at: '2026-07-06T00:00:00Z',
  status: 'open',
  exit_reasons: [],
  score: {
    forward_bars: 42,
    forward_return: 0.08,
    forward_sharpe: 0.9,
    buy_and_hold_return: -0.146,
    buy_and_hold_sharpe: -0.4,
    beats_buy_and_hold: true,
    forward_trades: 7,
    as_of: '2026-07-08T00:00:00Z',
    forward_equity: [],
  },
}

const closed: PaperPosition = {
  symbol: 'LOW',
  strategy_name: 'rsi_mean_reversion',
  parameters: { period: 14 },
  frozen_at: '2026-07-06T00:00:00Z',
  status: 'closed',
  closed_at: '2026-08-01T00:00:00Z',
  exit_reasons: ['rolling Sharpe -0.10 <= 0.0 (edge has decayed)'],
  score: null,
}

test('renders a row per position with symbol, strategy and forward Sharpe', () => {
  render(<PaperPortfolioTable positions={[open]} />)
  expect(screen.getByRole('cell', { name: 'CRM' })).toBeInTheDocument()
  expect(screen.getByRole('cell', { name: 'trend_filtered_mean_reversion' })).toBeInTheDocument()
  expect(screen.getByRole('cell', { name: '0.90' })).toBeInTheDocument()
  expect(screen.getByText(/42 forward bars/i)).toBeInTheDocument()
})

test('renders a position that has never traded as unmeasured, not as a score of zero', () => {
  // ADR-073: an all-zero forward series has Sharpe 0.0 by the degenerate-series guard. The table
  // used to render that as a real 0.00 next to a "beats" colour, which is how 18 of the book's
  // closed positions looked healthy right up until they were cut for a decayed edge they never had.
  const untraded: PaperPosition = {
    ...open,
    score: {
      ...open.score!,
      forward_bars: 21,
      forward_trades: 0,
      forward_return: 0,
      forward_sharpe: 0,
      beats_buy_and_hold: false,
    },
  }
  render(<PaperPortfolioTable positions={[untraded]} />)
  expect(screen.getByText(/no nonzero forward evidence recorded — 0 forward turnover events in 21 forward bars/i)).toBeInTheDocument()
  expect(screen.queryByRole('cell', { name: '0.00' })).not.toBeInTheDocument()
})

test('flags a traded position that lags buy-and-hold, not just one that beats it', () => {
  // The 'beats'/'lags' class only applies once a position has actually traded (untraded rows
  // render unmeasured instead, per the test above) — this is the other half of that branch,
  // never exercised: a real trade count with beats_buy_and_hold false.
  const lagging: PaperPosition = {
    ...open,
    score: { ...open.score!, beats_buy_and_hold: false },
  }
  render(<PaperPortfolioTable positions={[lagging]} />)
  const sharpeCell = screen.getByRole('cell', { name: '0.90' })
  expect(sharpeCell).toHaveClass('lags')
  expect(sharpeCell).not.toHaveClass('beats')
})

test('summarizes the position count and open count', () => {
  render(<PaperPortfolioTable positions={[open, closed]} />)
  expect(screen.getByText(/2 positions · 1 open/i)).toBeInTheDocument()
})

test('styles open vs closed positions differently and shows the status badge', () => {
  render(<PaperPortfolioTable positions={[open, closed]} />)
  const openRow = screen.getByRole('cell', { name: 'CRM' }).closest('tr')
  const closedRow = screen.getByRole('cell', { name: 'LOW' }).closest('tr')
  expect(openRow).toHaveClass('open')
  expect(closedRow).toHaveClass('closed')
  expect(screen.getByText('open')).toBeInTheDocument()
  expect(screen.getByText('closed')).toBeInTheDocument()
})

test('lists exit reasons for a closed position', () => {
  render(<PaperPortfolioTable positions={[closed]} />)
  expect(screen.getByText(/edge has decayed/i)).toBeInTheDocument()
})

test('shows a "no forward data yet" note when an open position has no score', () => {
  render(<PaperPortfolioTable positions={[{ ...open, score: null }]} />)
  expect(screen.getByText(/no forward data yet/i)).toBeInTheDocument()
})

test('renders an empty state when there are no positions', () => {
  render(<PaperPortfolioTable positions={[]} />)
  expect(screen.getByText(/no paper positions yet/i)).toBeInTheDocument()
})

test('uses singular "bar" for a one-bar-old scored position, traded and untraded alike', () => {
  // Every other fixture's forward_bars is 21 or 42 — the singular branch of both the
  // "not yet measurable" and the normal "N forward bars" text never ran.
  render(
    <PaperPortfolioTable
      positions={[
        { ...open, symbol: 'TRADED1', score: { ...open.score!, forward_bars: 1 } },
        {
          ...open,
          symbol: 'UNTRADED1',
          score: { ...open.score!, forward_bars: 1, forward_trades: 0, forward_return: 0, forward_sharpe: 0 },
        },
      ]}
    />,
  )
  expect(screen.getByText(/^1 forward bar$/i)).toBeInTheDocument()
  expect(screen.getByText(/no nonzero forward evidence recorded — 0 forward turnover events in 1 forward bar$/i)).toBeInTheDocument()
})

test.each([
  { label: 'legacy nonzero scores', sharpe: 0.9, returns: 0.08, curve: [] },
  { label: 'return only', sharpe: 0, returns: -0.2, curve: [] },
  { label: 'Sharpe only', sharpe: 0.9, returns: 0, curve: [] },
  { label: 'round-trip curve', sharpe: 0, returns: 0, curve: [1, 1.2, 1] },
  { label: 'first-period movement', sharpe: 0, returns: 0, curve: [1.2, 1, 1] },
  { label: 'tiny nonzero scalar', sharpe: 0, returns: Number.MIN_VALUE, curve: [] },
])('preserves served zero-turnover evidence: $label', ({ sharpe, returns, curve }) => {
  const scored: PaperPosition = { ...open, score: {
    ...open.score!, forward_bars: 3, forward_trades: 0,
    forward_sharpe: sharpe, forward_return: returns,
    forward_equity: curve.map((value, index) => ({
      timestamp: `2026-07-0${index + 7}T00:00:00Z`, strategy_equity: value, buy_and_hold_equity: 1,
    })),
  } }
  render(<PaperPortfolioTable positions={[scored]} />)
  const cells = within(screen.getByRole('cell', { name: 'CRM' }).closest('tr')!).getAllByRole('cell')
  expect(cells[3]).toHaveTextContent(new RegExp(`^${sharpe.toFixed(2).replace('.', '\\.')}$`))
  expect(cells[3]).toHaveClass('beats')
  expect(cells[5]).toHaveTextContent(`${(returns * 100).toFixed(1)}%`)
  expect(cells[6]).toHaveTextContent('0 forward turnover events in 3 forward bars')
  expect(screen.queryByText(/no nonzero forward evidence recorded/i)).not.toBeInTheDocument()
})

test('retains the server comparison flag for zero-turnover evidence', () => {
  render(<PaperPortfolioTable positions={[{ ...open, score: {
    ...open.score!, forward_trades: 0, beats_buy_and_hold: false,
  } }]} />)
  const cell = screen.getByRole('cell', { name: '0.90' })
  expect(cell).toHaveClass('lags')
  expect(cell).not.toHaveClass('beats')
})

test.each([{ curve: [] }, { curve: [1, 1, 1] }])('benchmark movement alone does not supply strategy evidence: %j', ({ curve }) => {
  render(<PaperPortfolioTable positions={[{ ...open, score: {
    ...open.score!, forward_bars: 3, forward_trades: 0, forward_return: -0, forward_sharpe: 0,
    forward_equity: curve.map((value, index) => ({
      timestamp: `2026-07-0${index + 7}T00:00:00Z`, strategy_equity: value, buy_and_hold_equity: 1.2,
    })),
  } }]} />)
  const cells = within(screen.getByRole('cell', { name: 'CRM' }).closest('tr')!).getAllByRole('cell')
  expect(cells[3]).toHaveTextContent('—')
  expect(cells[3]).not.toHaveClass('beats')
  expect(cells[3]).not.toHaveClass('lags')
  expect(cells[5]).toHaveTextContent('—')
  expect(screen.getByText(/no nonzero forward evidence recorded/i)).toBeInTheDocument()
})

test('qualifies legacy default counts without inferring historical execution', () => {
  render(<PaperPortfolioTable positions={[open]} />)
  expect(screen.getByText(/legacy default-zero counts do not attest historical execution/i)).toBeInTheDocument()
})
