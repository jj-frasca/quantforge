import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

import type { StrategyCatalog } from '../types/strategies'

// Default catalog mirrors the production backend so any test that mounts
// BacktestResultsPage / ValidationReportPage gets a sensible form rendered
// out of the box. Individual tests can server.use(...) to override.
export const defaultStrategyCatalog: StrategyCatalog = [
  {
    name: 'sma',
    label: 'SMA Crossover',
    description: 'Trend-following baseline.',
    category: 'Trend',
    summary: 'Buys when the recent average has been rising; sells when it has been falling.',
    citations: [],
    parameters: [
      { name: 'fast', type: 'int', default: 20, minimum: 1, label: 'Fast window' },
      { name: 'slow', type: 'int', default: 50, minimum: 2, label: 'Slow window' },
    ],
  },
  {
    name: 'momentum',
    label: 'Time-Series Momentum',
    description: 'Sign of trailing returns.',
    category: 'Trend',
    summary: 'Buys what has been going up over the past few months; sells what has been going down.',
    citations: [],
    parameters: [
      { name: 'lookback', type: 'int', default: 60, minimum: 1, label: 'Lookback window' },
      { name: 'skip', type: 'int', default: 5, minimum: 0, label: 'Skip bars' },
    ],
  },
  {
    name: 'mean_reversion',
    label: 'Mean Reversion (z-score)',
    description: 'Trade deviations from a rolling mean.',
    category: 'Mean Reversion',
    summary: 'Bets the price will snap back toward its recent average.',
    citations: [],
    parameters: [
      { name: 'window', type: 'int', default: 20, minimum: 2, label: 'Window' },
      { name: 'k', type: 'float', default: 2.0, minimum: 0.1, step: 0.1, label: 'k' },
    ],
  },
]

export const server = setupServer(
  http.get('/api/v1/strategies', () => HttpResponse.json(defaultStrategyCatalog)),
  // Lab dashboard (WP-D/WP-E) defaults to empty so any test mounting the Live page gets a
  // resolved request out of the box; individual tests server.use(...) to populate.
  http.get('/api/v1/leaderboard', () => HttpResponse.json([])),
  http.get('/api/v1/paper-portfolio', () => HttpResponse.json([])),
)
