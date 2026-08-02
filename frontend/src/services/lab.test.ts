import { http, HttpResponse } from 'msw'

import { server } from '../test/server'
import {
  requestCrossSectional,
  requestGraduates,
  requestLeaderboard,
  requestPaperPortfolio,
} from './lab'

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

test('requestGraduates parses the graduate rows', async () => {
  server.use(
    http.get('/api/v1/graduates', () =>
      HttpResponse.json([
        {
          symbol: 'CRM',
          strategy_name: 'trend_filtered_mean_reversion',
          deflated_sharpe: 0.44,
          holdout_sharpe: 0.5,
          survives_universe_deflation: false,
          undervaluation_score: 0.7,
        },
      ]),
    ),
  )
  const rows = await requestGraduates()
  expect(rows).toHaveLength(1)
  expect(rows[0].undervaluation_score).toBe(0.7)
})

test('requestGraduates throws on a non-2xx response', async () => {
  server.use(http.get('/api/v1/graduates', () => new HttpResponse(null, { status: 500 })))
  await expect(requestGraduates()).rejects.toThrow(/Graduates request failed \(500\)/)
})

test('requestCrossSectional parses the latest hunt view', async () => {
  server.use(
    http.get('/api/v1/cross-sectional', () =>
      HttpResponse.json({
        created_at: '2026-07-26T10:00:00Z',
        universe_size: 51,
        best_strategy_name: 'xs_momentum',
        graduated: false,
        graduate_holdout_sharpe: null,
        trials: [
          {
            strategy_name: 'xs_momentum',
            observed_sharpe: 0.5,
            deflated_sharpe: -0.08,
            pbo: 0.44,
            parameter_stability_score: 0.22,
          },
        ],
      }),
    ),
  )
  const view = await requestCrossSectional()
  expect(view?.universe_size).toBe(51)
  expect(view?.trials[0].strategy_name).toBe('xs_momentum')
})

test('requestCrossSectional returns null when no hunt has run', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json(null)))
  await expect(requestCrossSectional()).resolves.toBeNull()
})

test('requestCrossSectional throws on a non-2xx response', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => new HttpResponse(null, { status: 500 })))
  await expect(requestCrossSectional()).rejects.toThrow(/Cross-sectional request failed \(500\)/)
})
