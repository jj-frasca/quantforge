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
    citations: [],
    parameters: [
      { name: 'window', type: 'int', default: 20, minimum: 2, label: 'Window' },
      { name: 'k', type: 'float', default: 2.0, minimum: 0.1, step: 0.1, label: 'k' },
    ],
  },
]

export const server = setupServer(
  http.get('/api/v1/strategies', () => HttpResponse.json(defaultStrategyCatalog)),
)
