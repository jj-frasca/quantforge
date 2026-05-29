import { http, HttpResponse } from 'msw'

import { server } from '../test/server'
import { passingReport } from '../test/utils'
import type { ValidateRequest } from '../types/validation'
import { requestValidation } from './api'

const request: ValidateRequest = {
  symbol: 'AAPL',
  strategy: 'sma',
  start_date: '2020-01-01T00:00:00Z',
  end_date: '2024-01-01T00:00:00Z',
}

test('requestValidation returns a parsed report on success', async () => {
  server.use(http.post('/api/v1/validate', () => HttpResponse.json(passingReport)))
  const report = await requestValidation(request)
  expect(report).toEqual(passingReport)
})

test('requestValidation throws on a non-2xx response', async () => {
  server.use(
    http.post('/api/v1/validate', () => HttpResponse.json({ detail: 'bad' }, { status: 422 })),
  )
  await expect(requestValidation(request)).rejects.toThrow(/422/)
})
