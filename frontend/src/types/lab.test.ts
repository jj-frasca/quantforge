import {
  crossSectionalResponseSchema,
  graduatesSchema,
  leaderboardSchema,
  paperPortfolioSchema,
  nullCalibrationSchema,
  type LeaderboardRow,
  type PaperPosition,
} from './lab'

test('nullCalibrationSchema preserves the measured history identity', () => {
  const parsed = nullCalibrationSchema.parse({
    n_symbols: 1,
    n_graduates: 0,
    false_graduation_rate: 0,
    n_clear_deflation_bar: 0,
    deflation_bar: 1,
    max_deflated_sharpe: -0.1,
    max_holdout_sharpe: null,
    gate_config_version: 'gate',
    search_config_version: 'search',
    null_mode: 'iid_normal',
    n_bars: [5400],
  })

  expect(parsed.n_bars).toEqual([5400])
})

test('graduatesSchema parses a graduate row incl. undervaluation + deflation verdict', () => {
  const raw = [
    {
      symbol: 'CRM',
      strategy_name: 'trend_filtered_mean_reversion',
      deflated_sharpe: 0.44,
      holdout_sharpe: 0.5,
      survives_universe_deflation: false,
      undervaluation_score: 0.7,
    },
  ]
  const parsed = graduatesSchema.parse(raw)
  expect(parsed[0].survives_universe_deflation).toBe(false)
  expect(parsed[0].undervaluation_score).toBe(0.7)
})

test('graduatesSchema tolerates null undervaluation / deflation (unscorable name)', () => {
  const parsed = graduatesSchema.parse([
    {
      symbol: 'SPY',
      strategy_name: 'sma',
      deflated_sharpe: 0.3,
      holdout_sharpe: 0.2,
      survives_universe_deflation: null,
      undervaluation_score: null,
    },
  ])
  expect(parsed[0].undervaluation_score).toBeNull()
})

test('crossSectionalResponseSchema parses a hunt view with trials', () => {
  const parsed = crossSectionalResponseSchema.parse({
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
        ic_mean: 0.021,
        ic_t_stat: 3.42,
      },
    ],
  })
  expect(parsed?.universe_size).toBe(51)
  expect(parsed?.trials[0].pbo).toBe(0.44)
  expect(parsed?.trials[0].ic_mean).toBe(0.021)
})

test('crossSectionalResponseSchema accepts a trial recorded before ADR-035 (no IC)', () => {
  const parsed = crossSectionalResponseSchema.parse({
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
  })
  expect(parsed?.trials[0].ic_mean).toBeUndefined()
})

test('crossSectionalResponseSchema parses null (no hunt yet)', () => {
  expect(crossSectionalResponseSchema.parse(null)).toBeNull()
})

test('leaderboardSchema parses a graduate row with holdout + deflation fields', () => {
  const raw = [
    {
      symbol: 'CRM',
      strategy_name: 'trend_filtered_mean_reversion',
      deflated_sharpe: 0.28,
      graduated: true,
      holdout_sharpe: 0.44,
      survives_universe_deflation: false,
    },
  ]
  const parsed = leaderboardSchema.parse(raw)
  expect(parsed[0].symbol).toBe('CRM')
  expect(parsed[0].graduated).toBe(true)
  expect(parsed[0].holdout_sharpe).toBe(0.44)
})

test('leaderboardSchema tolerates a non-graduate row with null holdout fields', () => {
  const raw = [
    {
      symbol: 'SPY',
      strategy_name: 'donchian_breakout',
      deflated_sharpe: -0.12,
      graduated: false,
      holdout_sharpe: null,
      survives_universe_deflation: null,
    },
  ]
  const parsed = leaderboardSchema.parse(raw)
  expect(parsed[0].graduated).toBe(false)
  expect(parsed[0].holdout_sharpe).toBeNull()
})

test('paperPortfolioSchema parses an open position with a forward score + equity series', () => {
  const raw = [
    {
      symbol: 'CRM',
      strategy_name: 'trend_filtered_mean_reversion',
      parameters: { window: 20, k: 2.0 },
      frozen_at: '2026-07-06T00:00:00Z',
      score: {
        forward_bars: 2,
        forward_return: 0.08,
        forward_sharpe: 0.9,
        buy_and_hold_return: -0.146,
        buy_and_hold_sharpe: -0.4,
        beats_buy_and_hold: true,
        forward_trades: 7,
        as_of: '2026-07-08T00:00:00Z',
        forward_equity: [
          { timestamp: '2026-07-07T00:00:00Z', strategy_equity: 1.02, buy_and_hold_equity: 0.99 },
          { timestamp: '2026-07-08T00:00:00Z', strategy_equity: 1.08, buy_and_hold_equity: 0.854 },
        ],
      },
      status: 'open',
      closed_at: null,
      exit_reasons: [],
    },
  ]
  const parsed = paperPortfolioSchema.parse(raw)
  expect(parsed[0].status).toBe('open')
  expect(parsed[0].score?.beats_buy_and_hold).toBe(true)
  expect(parsed[0].score?.forward_equity).toHaveLength(2)
  expect(parsed[0].score?.forward_equity[0].strategy_equity).toBe(1.02)
})

test('forwardScoreSchema defaults forward_equity to [] when absent (pre-ADR-023 scores)', () => {
  const raw = [
    {
      symbol: 'AAPL',
      strategy_name: 'sma',
      parameters: {},
      frozen_at: '2026-07-06T00:00:00Z',
      score: {
        forward_bars: 0,
        forward_return: 0.0,
        forward_sharpe: 0.0,
        buy_and_hold_return: 0.0,
        buy_and_hold_sharpe: 0.0,
        beats_buy_and_hold: false,
        forward_trades: 7,
        as_of: '2026-07-08T00:00:00Z',
      },
      status: 'open',
      exit_reasons: [],
    },
  ]
  const parsed = paperPortfolioSchema.parse(raw)
  expect(parsed[0].score?.forward_equity).toEqual([])
})

test('paperPortfolioSchema parses a closed position with exit reasons and null score', () => {
  const raw = [
    {
      symbol: 'LOW',
      strategy_name: 'rsi_mean_reversion',
      parameters: { period: 14 },
      frozen_at: '2026-07-06T00:00:00Z',
      score: null,
      status: 'closed',
      closed_at: '2026-08-01T00:00:00Z',
      exit_reasons: ['rolling Sharpe -0.10 <= 0.0 (edge has decayed)'],
    },
  ]
  const parsed = paperPortfolioSchema.parse(raw)
  expect(parsed[0].status).toBe('closed')
  expect(parsed[0].score).toBeNull()
  expect(parsed[0].exit_reasons).toHaveLength(1)
})

test('paperPortfolioSchema rejects an unknown status (boundary guard)', () => {
  const raw = [
    {
      symbol: 'AAPL',
      strategy_name: 'sma',
      parameters: {},
      frozen_at: '2026-07-06T00:00:00Z',
      status: 'paused',
      exit_reasons: [],
    },
  ]
  expect(() => paperPortfolioSchema.parse(raw)).toThrow()
})

// Type-level smoke: the inferred types are exported for components to consume.
test('exported types are usable', () => {
  const row: LeaderboardRow = {
    symbol: 'X',
    strategy_name: 'sma',
    deflated_sharpe: 0,
    graduated: false,
  }
  const pos: PaperPosition = {
    symbol: 'X',
    strategy_name: 'sma',
    parameters: {},
    frozen_at: '2026-07-06T00:00:00Z',
    status: 'open',
    exit_reasons: [],
  }
  expect(row.symbol).toBe(pos.symbol)
})
