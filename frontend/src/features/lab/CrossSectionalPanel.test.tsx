import { screen, waitForElementToBeRemoved } from '@testing-library/react'
import { http, HttpResponse } from 'msw'

import { server } from '../../test/server'
import { renderWithClient } from '../../test/utils'
import { CrossSectionalPanel } from './CrossSectionalPanel'

const view = {
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
    {
      strategy_name: 'xs_reversal',
      observed_sharpe: -1.2,
      deflated_sharpe: -1.68,
      pbo: 0.0,
      parameter_stability_score: 0.79,
    },
  ],
}

test('renders the latest hunt: universe size, best strategy and per-strategy trials', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json(view)))
  renderWithClient(<CrossSectionalPanel />)

  expect(await screen.findByRole('cell', { name: 'xs_momentum' })).toBeInTheDocument()
  expect(screen.getByText(/51 names/)).toBeInTheDocument()
  expect(screen.getByText(/best: xs_momentum/)).toBeInTheDocument()
  expect(screen.getByText('no graduate')).toBeInTheDocument()
  // PBO + parameter stability render as percentages.
  expect(screen.getByRole('cell', { name: '44%' })).toBeInTheDocument()
})

test('renders the empty state when no cross-sectional hunt has run (null)', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json(null)))
  renderWithClient(<CrossSectionalPanel />)

  expect(await screen.findByText(/no cross-sectional hunt has run yet/i)).toBeInTheDocument()
})

test('shows a graduate verdict + holdout Sharpe when a strategy graduated', async () => {
  server.use(
    http.get('/api/v1/cross-sectional', () =>
      HttpResponse.json({ ...view, graduated: true, graduate_holdout_sharpe: 0.63 }),
    ),
  )
  renderWithClient(<CrossSectionalPanel />)

  expect(await screen.findByText('graduate')).toBeInTheDocument()
  expect(screen.getByText(/holdout Sharpe 0.63/)).toBeInTheDocument()
})

test('shows an error message when the cross-sectional endpoint fails', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => new HttpResponse(null, { status: 500 })))
  renderWithClient(<CrossSectionalPanel />)

  expect(await screen.findByText(/could not load the cross-sectional hunt/i)).toBeInTheDocument()
})

test('shows a loading indicator while the hunt is pending', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json(view)))
  renderWithClient(<CrossSectionalPanel />)

  await waitForElementToBeRemoved(() => screen.queryByText(/loading cross-sectional hunt/i))
  expect(await screen.findByRole('cell', { name: 'xs_momentum' })).toBeInTheDocument()
})
