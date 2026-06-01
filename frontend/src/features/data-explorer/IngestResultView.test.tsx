// IngestResultView: renders the stored/not-stored verdict, the metrics, and the
// quality issues sorted by severity (errors first, then warnings, then info). An
// empty issues list should render an explicit "no issues" note, not silence.
import { render, screen, within } from '@testing-library/react'

import type { IngestResponse } from '../../types/ingest'
import { IngestResultView } from './IngestResultView'

const cleanResult: IngestResponse = {
  symbol: 'AAPL',
  bars_ingested: 30,
  stored: true,
  quality_report: {
    symbol: 'AAPL',
    checked_at: '2024-01-02T00:00:00Z',
    issues: [],
    passed: true,
  },
}

const failedResult: IngestResponse = {
  symbol: 'AAPL',
  bars_ingested: 5,
  stored: false,
  quality_report: {
    symbol: 'AAPL',
    checked_at: '2024-01-02T00:00:00Z',
    issues: [
      {
        check: 'stale_data',
        severity: 'info',
        message: 'flags potential stale window of 2 days',
      },
      { check: 'insufficient_data', severity: 'error', message: 'flags potential insufficiency (5 bars)' },
      { check: 'missing_bars', severity: 'warning', message: 'flags potential gap of 3 bars' },
    ],
    passed: false,
  },
}

test('renders a stored verdict and the bar count', () => {
  render(<IngestResultView result={cleanResult} />)
  expect(screen.getByRole('status')).toHaveTextContent(/stored 30 bars/i)
  expect(screen.getByText('30')).toBeInTheDocument()
  expect(screen.getByText(/no data-quality issues flagged/i)).toBeInTheDocument()
})

test('renders a failed verdict and surfaces issues with errors first', () => {
  render(<IngestResultView result={failedResult} />)
  expect(screen.getByRole('status')).toHaveTextContent(/not stored/i)
  const issuesList = screen.getByLabelText('quality issues')
  const items = within(issuesList).getAllByRole('listitem')
  expect(items).toHaveLength(3)
  expect(items[0]).toHaveTextContent(/insufficient_data/i)
  expect(items[0]).toHaveTextContent(/\[error\]/)
  expect(items[1]).toHaveTextContent(/missing_bars/i)
  expect(items[2]).toHaveTextContent(/stale_data/i)
})
