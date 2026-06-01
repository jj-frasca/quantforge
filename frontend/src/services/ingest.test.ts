// requestIngest: returns a Zod-parsed response on 200; on a non-2xx response throws an
// error that includes the status and the backend `detail`. Backend mocked with MSW.
import { http, HttpResponse } from 'msw'

import { server } from '../test/server'
import type { IngestRequest, IngestResponse } from '../types/ingest'
import { requestIngest } from './ingest'

const request: IngestRequest = {
  symbol: 'AAPL',
  start_date: '2024-01-01T00:00:00Z',
  end_date: '2024-12-01T00:00:00Z',
}

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

test('requestIngest returns a parsed response on success', async () => {
  server.use(http.post('/api/v1/ingest', () => HttpResponse.json(successResponse)))
  const response = await requestIngest(request)
  expect(response).toEqual(successResponse)
})

test('requestIngest throws on a non-2xx response, surfacing the backend detail', async () => {
  server.use(
    http.post('/api/v1/ingest', () =>
      HttpResponse.json({ detail: 'unknown symbol' }, { status: 502 }),
    ),
  )
  await expect(requestIngest(request)).rejects.toThrow(/502.*unknown symbol/)
})
