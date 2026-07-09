import { http, HttpResponse } from 'msw'

import { server } from '../test/server'
import { requestLeaderboard, requestPaperPortfolio } from './lab'

test('requestLeaderboard parses the leaderboard rows', async () => {
  server.use(
    http.get('/api/v1/leaderboard', () =>
      HttpResponse.json([
        {
          symbol: 'CRM',
          strategy_name: 'trend_filtered_mean_reversion',
          deflated_sharpe: 0.28,
          graduated: true,
          holdout_sharpe: 0.44,
          survives_universe_deflation: false,
        },
      ]),
    ),
  )
  const rows = await requestLeaderboard()
  expect(rows).toHaveLength(1)
  expect(rows[0].symbol).toBe('CRM')
})

test('requestLeaderboard throws on a non-2xx response', async () => {
  server.use(
    http.get('/api/v1/leaderboard', () => new HttpResponse(null, { status: 500 })),
  )
  await expect(requestLeaderboard()).rejects.toThrow(/Leaderboard request failed \(500\)/)
})

test('requestPaperPortfolio parses the positions', async () => {
  server.use(
    http.get('/api/v1/paper-portfolio', () =>
      HttpResponse.json([
        {
          symbol: 'LOW',
          strategy_name: 'rsi_mean_reversion',
          parameters: { period: 14 },
          frozen_at: '2026-07-06T00:00:00Z',
          score: null,
          status: 'open',
          closed_at: null,
          exit_reasons: [],
        },
      ]),
    ),
  )
  const positions = await requestPaperPortfolio()
  expect(positions[0].symbol).toBe('LOW')
})

test('requestPaperPortfolio throws on a non-2xx response', async () => {
  server.use(
    http.get('/api/v1/paper-portfolio', () => new HttpResponse(null, { status: 503 })),
  )
  await expect(requestPaperPortfolio()).rejects.toThrow(/Paper portfolio request failed \(503\)/)
})
