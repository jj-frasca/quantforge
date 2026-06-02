// DataExplorerPage: renders the form; submit sends /ingest body, renders IngestResultView
// and PriceChart on success; surfaces the backend `detail` on failure.
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import { server } from '../../test/server'
import { renderWithClient } from '../../test/utils'
import type { BarsResponse } from '../../types/bars'
import type { IngestResponse } from '../../types/ingest'
import { DataExplorerPage } from './DataExplorerPage'

const successIngest: IngestResponse = {
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

const successBars: BarsResponse = {
  symbol: 'AAPL',
  n_bars: 1,
  bars: [
    {
      timestamp_utc: '2024-01-02T00:00:00Z',
      open: 100,
      high: 101,
      low: 99,
      close: 100.5,
      volume: 1_000_000,
    },
  ],
}

test('renders the form with sensible defaults', () => {
  renderWithClient(<DataExplorerPage />)
  expect(screen.getByLabelText(/symbol/i)).toHaveValue('AAPL')
  expect(screen.getByRole('button', { name: /ingest data/i })).toBeEnabled()
})

test('submitting fires /ingest + /bars and renders both result + chart', async () => {
  let ingestBody: unknown
  server.use(
    http.post('/api/v1/ingest', async ({ request }) => {
      ingestBody = await request.json()
      return HttpResponse.json(successIngest)
    }),
    http.get('/api/v1/bars', () => HttpResponse.json(successBars)),
  )

  renderWithClient(<DataExplorerPage />)
  await userEvent.click(screen.getByRole('button', { name: /ingest data/i }))

  expect(await screen.findByRole('status')).toHaveTextContent(/stored 30 bars/i)
  expect(await screen.findByLabelText('price chart')).toBeInTheDocument()
  expect(screen.getByText(/last close 100\.50/)).toBeInTheDocument()
  expect(ingestBody).toEqual({
    symbol: 'AAPL',
    start_date: '2024-01-01T00:00:00Z',
    end_date: '2024-12-01T00:00:00Z',
  })
})

test('surfaces the backend detail when ingestion fails', async () => {
  server.use(
    http.post('/api/v1/ingest', () =>
      HttpResponse.json({ detail: 'unknown symbol' }, { status: 502 }),
    ),
    http.get('/api/v1/bars', () =>
      HttpResponse.json({ symbol: 'AAPL', n_bars: 0, bars: [] }),
    ),
  )
  renderWithClient(<DataExplorerPage />)
  await userEvent.click(screen.getByRole('button', { name: /ingest data/i }))
  await waitFor(() => {
    expect(screen.getByRole('alert')).toHaveTextContent(/unknown symbol/i)
  })
})
