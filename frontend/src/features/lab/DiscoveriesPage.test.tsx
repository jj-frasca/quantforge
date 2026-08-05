import { screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'

import { server } from '../../test/server'
import { renderWithClient } from '../../test/utils'
import { DiscoveriesPage } from './DiscoveriesPage'

test('renders the equity-curve, graduates and cross-sectional panels', async () => {
  server.use(
    http.get('/api/v1/graduates', () =>
      HttpResponse.json([
        {
          symbol: 'CRM',
          strategy_name: 'trend_filtered_mean_reversion',
          deflated_sharpe: 0.44,
          holdout_sharpe: 0.5,
          survives_universe_deflation: true,
          undervaluation_score: null,
        },
      ]),
    ),
    http.get('/api/v1/cross-sectional', () => HttpResponse.json(null)),
  )
  renderWithClient(<DiscoveriesPage />)

  expect(await screen.findByLabelText('discoveries page')).toBeInTheDocument()
  // Equity-curve headline "are we making money?" view sits at the top of the page.
  expect(screen.getByLabelText('equity curve section')).toBeInTheDocument()
  expect(screen.getByLabelText('graduates section')).toBeInTheDocument()
  expect(screen.getByLabelText('cross-sectional section')).toBeInTheDocument()
  // Graduate headline row renders; cross-sectional shows its empty state.
  expect(await screen.findByRole('cell', { name: 'CRM' })).toBeInTheDocument()
  expect(await screen.findByText(/no cross-sectional hunt has run yet/i)).toBeInTheDocument()
})
