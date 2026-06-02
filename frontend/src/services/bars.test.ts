// requestBars: returns a Zod-parsed response on 200; sends the query as URL params;
// throws with backend `detail` on non-2xx. Backend mocked with MSW.
import { http, HttpResponse } from 'msw'

import { server } from '../test/server'
import type { BarsResponse } from '../types/bars'
import { requestBars } from './bars'

const query = {
  symbol: 'AAPL',
  start_date: '2024-01-01T00:00:00Z',
  end_date: '2024-12-01T00:00:00Z',
}

const successResponse: BarsResponse = {
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

test('requestBars sends the query and returns a parsed response', async () => {
  let receivedUrl = ''
  server.use(
    http.get('/api/v1/bars', ({ request }) => {
      receivedUrl = request.url
      return HttpResponse.json(successResponse)
    }),
  )
  const response = await requestBars(query)
  expect(response).toEqual(successResponse)
  expect(receivedUrl).toContain('symbol=AAPL')
  expect(receivedUrl).toContain('start_date=')
})

test('requestBars throws on a non-2xx response with the backend detail', async () => {
  server.use(
    http.get('/api/v1/bars', () => HttpResponse.json({ detail: 'bad range' }, { status: 422 })),
  )
  await expect(requestBars(query)).rejects.toThrow(/422.*bad range/)
})
