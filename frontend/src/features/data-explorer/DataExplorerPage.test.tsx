// DataExplorerPage: renders the form; submit sends the request body the backend expects
// and renders the IngestResultView on success; surfaces the backend `detail` on failure.
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import { server } from '../../test/server'
import { renderWithClient } from '../../test/utils'
import type { IngestResponse } from '../../types/ingest'
import { DataExplorerPage } from './DataExplorerPage'

const successResponse: IngestResponse = {
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

test('renders the form with sensible defaults', () => {
  renderWithClient(<DataExplorerPage />)
  expect(screen.getByLabelText(/symbol/i)).toHaveValue('AAPL')
  expect(screen.getByRole('button', { name: /ingest data/i })).toBeEnabled()
})

test('submitting the form sends an ISO body and renders the result on success', async () => {
  let receivedBody: unknown
  server.use(
    http.post('/api/v1/ingest', async ({ request }) => {
      receivedBody = await request.json()
      return HttpResponse.json(successResponse)
    }),
  )

  renderWithClient(<DataExplorerPage />)
  await userEvent.click(screen.getByRole('button', { name: /ingest data/i }))

  expect(await screen.findByRole('status')).toHaveTextContent(/stored 30 bars/i)
  expect(receivedBody).toEqual({
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
  )
  renderWithClient(<DataExplorerPage />)
  await userEvent.click(screen.getByRole('button', { name: /ingest data/i }))
  await waitFor(() => {
    expect(screen.getByRole('alert')).toHaveTextContent(/unknown symbol/i)
  })
})
