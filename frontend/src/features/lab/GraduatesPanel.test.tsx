import { screen, waitForElementToBeRemoved } from '@testing-library/react'
import { http, HttpResponse } from 'msw'

import { server } from '../../test/server'
import { renderWithClient } from '../../test/utils'
import { GraduatesPanel } from './GraduatesPanel'

const graduates = [
  {
    symbol: 'CRM',
    strategy_name: 'trend_filtered_mean_reversion',
    deflated_sharpe: 0.44,
    holdout_sharpe: 0.5,
    survives_universe_deflation: true,
    undervaluation_score: 0.7,
  },
  {
    symbol: 'LOW',
    strategy_name: 'rsi_mean_reversion',
    deflated_sharpe: 0.3,
    holdout_sharpe: 0.2,
    survives_universe_deflation: false,
    undervaluation_score: null,
  },
]

test('renders the graduates table with symbol, strategy and deflation verdict', async () => {
  server.use(http.get('/api/v1/graduates', () => HttpResponse.json(graduates)))
  renderWithClient(<GraduatesPanel />)

  expect(await screen.findByRole('cell', { name: 'CRM' })).toBeInTheDocument()
  expect(screen.getByRole('cell', { name: 'trend_filtered_mean_reversion' })).toBeInTheDocument()
  // Honest cross-symbol-selection caveat surfaces per row.
  expect(screen.getByText('survives')).toBeInTheDocument()
  expect(screen.getByText('selection-lucky')).toBeInTheDocument()
  // Undervaluation renders as a percentage, em dash when unscorable.
  expect(screen.getByRole('cell', { name: '70%' })).toBeInTheDocument()
  expect(screen.getByText('2 graduates · 1 survives universe deflation')).toBeInTheDocument()
})

test('renders the empty state when no strategy has graduated', async () => {
  server.use(http.get('/api/v1/graduates', () => HttpResponse.json([])))
  renderWithClient(<GraduatesPanel />)

  expect(await screen.findByText(/no strategy has cleared the gate/i)).toBeInTheDocument()
})

test('shows an error message when the graduates endpoint fails', async () => {
  server.use(http.get('/api/v1/graduates', () => new HttpResponse(null, { status: 500 })))
  renderWithClient(<GraduatesPanel />)

  expect(await screen.findByText(/could not load graduates/i)).toBeInTheDocument()
})

test('shows a loading indicator while the graduates are pending', async () => {
  server.use(http.get('/api/v1/graduates', () => HttpResponse.json(graduates)))
  renderWithClient(<GraduatesPanel />)

  await waitForElementToBeRemoved(() => screen.queryByText(/loading graduates/i))
  expect(await screen.findByRole('cell', { name: 'CRM' })).toBeInTheDocument()
})
