// requestBacktest: parses on 200; surfaces backend `detail` on non-2xx.
import { http, HttpResponse } from 'msw'

import { server } from '../test/server'
import type { BacktestRequest, BacktestResponse } from '../types/backtest'
import { requestBacktest } from './backtest'

const request: BacktestRequest = {
  symbol: 'AAPL',
  strategy: { name: 'sma', fast: 5, slow: 20 },
  start_date: '2024-01-01T00:00:00Z',
  end_date: '2024-12-01T00:00:00Z',
}

const successResponse: BacktestResponse = {
  symbol: 'AAPL',
  strategy_name: 'sma_crossover',
  parameters: { fast: 5, slow: 20 },
  n_trades: 12,
  cost_rate: 0.001,
  metrics: {
    sharpe: 1.5,
    max_drawdown: -0.1,
    total_return: 0.3,
    annualized_return: 0.12,
    annualized_vol: 0.08,
  },
  equity_curve: [
    { timestamp_utc: '2024-01-01T00:00:00Z', equity: 100_000 },
    { timestamp_utc: '2024-01-02T00:00:00Z', equity: 100_300 },
  ],
}

test('requestBacktest returns a parsed response on success', async () => {
  server.use(http.post('/api/v1/backtest', () => HttpResponse.json(successResponse)))
  const response = await requestBacktest(request)
  expect(response).toEqual(successResponse)
})

test('requestBacktest throws on non-2xx with backend detail', async () => {
  server.use(
    http.post('/api/v1/backtest', () =>
      HttpResponse.json({ detail: 'insufficient data' }, { status: 422 }),
    ),
  )
  await expect(requestBacktest(request)).rejects.toThrow(/422.*insufficient data/)
})
