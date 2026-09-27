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
  // Dates come from defaultDateRange(1) anchored to "today" — covered by
  // defaultDateRange.test.ts; here we just assert the rest of the body and the shape.
  expect(ingestBody).toMatchObject({ symbol: 'AAPL' })
  const dateRe = /^\d{4}-\d{2}-\d{2}T00:00:00Z$/
  const wireBody = ingestBody as { start_date: string; end_date: string }
  expect(wireBody.start_date).toMatch(dateRe)
  expect(wireBody.end_date).toMatch(dateRe)
})

test('editing symbol and date fields propagates to the ingest request', async () => {
  let ingestBody: { symbol?: string; start_date?: string; end_date?: string } | undefined
  server.use(
    http.post('/api/v1/ingest', async ({ request }) => {
      ingestBody = (await request.json()) as typeof ingestBody
      return HttpResponse.json(successIngest)
    }),
    http.get('/api/v1/bars', () => HttpResponse.json(successBars)),
  )

  renderWithClient(<DataExplorerPage />)
  await userEvent.clear(screen.getByLabelText(/symbol/i))
  await userEvent.type(screen.getByLabelText(/symbol/i), 'msft')

  const startInput = screen.getByLabelText(/start date/i)
  await userEvent.clear(startInput)
  await userEvent.type(startInput, '2022-01-15')
  const endInput = screen.getByLabelText(/end date/i)
  await userEvent.clear(endInput)
  await userEvent.type(endInput, '2023-02-20')

  await userEvent.click(screen.getByRole('button', { name: /ingest data/i }))
  await screen.findByRole('status')

  expect(ingestBody?.symbol).toBe('MSFT')
  expect(ingestBody?.start_date).toBe('2022-01-15T00:00:00Z')
  expect(ingestBody?.end_date).toBe('2023-02-20T00:00:00Z')
})

test('disables submit and shows an inline message for an equal or reversed date range', async () => {
  // FINDING-064: the backend (ADR-132) now rejects equal/reversed ranges with a 422 —
  // this form should catch it before submit rather than round-trip to find out.
  renderWithClient(<DataExplorerPage />)
  const startInput = screen.getByLabelText(/start date/i)
  const endInput = screen.getByLabelText(/end date/i)
  await userEvent.clear(startInput)
  await userEvent.type(startInput, '2021-01-01')
  await userEvent.clear(endInput)
  await userEvent.type(endInput, '2021-01-01')

  expect(screen.getByRole('alert')).toHaveTextContent(/start date must be before end date/i)
  expect(screen.getByRole('button', { name: /ingest data/i })).toBeDisabled()

  await userEvent.clear(endInput)
  await userEvent.type(endInput, '2022-01-01')
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: /ingest data/i })).not.toBeDisabled()
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
