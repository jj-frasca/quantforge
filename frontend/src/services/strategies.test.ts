// requestStrategies: parses the catalog on 200; throws with status on non-2xx.
import { http, HttpResponse } from 'msw'

import { server } from '../test/server'
import type { StrategyCatalog } from '../types/strategies'
import { requestStrategies } from './strategies'

const catalog: StrategyCatalog = [
  {
    name: 'sma',
    label: 'SMA Crossover',
    description: 'baseline',
    citations: [],
    parameters: [
      { name: 'fast', type: 'int', default: 20, label: 'Fast window' },
      { name: 'slow', type: 'int', default: 50, label: 'Slow window' },
    ],
  },
]

test('requestStrategies returns the parsed catalog on success', async () => {
  server.use(http.get('/api/v1/strategies', () => HttpResponse.json(catalog)))
  const result = await requestStrategies()
  expect(result).toEqual(catalog)
})

test('requestStrategies throws on non-2xx', async () => {
  server.use(
    http.get('/api/v1/strategies', () => HttpResponse.json({}, { status: 500 })),
  )
  await expect(requestStrategies()).rejects.toThrow(/500/)
})
