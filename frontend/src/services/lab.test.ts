import { http, HttpResponse } from 'msw'

import { server } from '../test/server'
import {
  requestCrossSectional,
  requestGraduates,
  requestLeaderboard,
  requestPaperPortfolio,
  requestWindowComparison,
  requestWindowExperiment,
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

// ADR-074: a null body means no symbol spans both windows. It must survive parsing as null rather
// than being coerced into an object of zeros, which would read as a measured absence of effect.
test('requestWindowComparison parses a measured comparison', async () => {
  server.use(
    http.get('/api/v1/window-comparison', () =>
      HttpResponse.json({
        n_symbols: 368,
        short_n_bars: 5446,
        long_n_bars: 9232,
        oos_delta_median: -0.038,
        oos_delta_ci_low: -0.06,
        oos_delta_ci_high: -0.009,
        in_sample_delta_median: 0.012,
        in_sample_delta_ci_low: -0.005,
        in_sample_delta_ci_high: 0.034,
        n_finalist_changed: 257,
        excess_n: 0,
        excess_delta_median: null,
        excess_delta_ci_low: null,
        excess_delta_ci_high: null,
      }),
    ),
  )
  const comparison = await requestWindowComparison()
  expect(comparison?.n_symbols).toBe(368)
  expect(comparison?.excess_delta_median).toBeNull()
})

test('requestWindowComparison returns null when nothing spans both windows', async () => {
  server.use(http.get('/api/v1/window-comparison', () => HttpResponse.json(null)))
  await expect(requestWindowComparison()).resolves.toBeNull()
})

test('requestWindowComparison throws on a non-2xx response', async () => {
  server.use(
    http.get('/api/v1/window-comparison', () => new HttpResponse(null, { status: 503 })),
  )
  await expect(requestWindowComparison()).rejects.toThrow(/Window comparison request failed \(503\)/)
})

// ADR-077: the frozen artifact is parsed, never derived. A missing artifact is null — an
// experiment nobody has run, which is not the same claim as an effect of zero.
test('requestWindowExperiment parses the frozen result and its boundary alpha', async () => {
  const side = {
    n_symbols: 368,
    short_n_bars: 5447,
    long_n_bars: 9232,
    oos_delta_median: -0.037,
    oos_delta_ci_low: -0.061,
    oos_delta_ci_high: -0.008,
    in_sample_delta_median: 0.014,
    in_sample_delta_ci_low: -0.004,
    in_sample_delta_ci_high: 0.036,
    n_finalist_changed: 258,
    excess_n: 200,
    excess_delta_median: -0.008,
    excess_delta_ci_low: -0.055,
    excess_delta_ci_high: 0.022,
  }
  server.use(
    http.get('/api/v1/window-experiment', () =>
      HttpResponse.json({
        sample: ['AAA', 'BBB'],
        criterion_alpha: 0.0294,
        criterion: side,
        at_look_one_alpha: { ...side, excess_delta_ci_high: 0.016 },
      }),
    ),
  )
  const experiment = await requestWindowExperiment()
  expect(experiment?.criterion_alpha).toBe(0.0294)
  expect(experiment?.criterion.excess_delta_median).toBe(-0.008)
  expect(experiment?.at_look_one_alpha.excess_delta_ci_high).toBe(0.016)
  expect(experiment?.sample).toHaveLength(2)
})

test('requestWindowExperiment returns null when the experiment has not been run', async () => {
  server.use(http.get('/api/v1/window-experiment', () => HttpResponse.json(null)))
  await expect(requestWindowExperiment()).resolves.toBeNull()
})

test('requestWindowExperiment throws on a non-2xx response', async () => {
  server.use(
    http.get('/api/v1/window-experiment', () => new HttpResponse(null, { status: 503 })),
  )
  await expect(requestWindowExperiment()).rejects.toThrow(/Window experiment request failed \(503\)/)
})
