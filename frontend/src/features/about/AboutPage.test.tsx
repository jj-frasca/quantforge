// AboutPage: renders the static methodology sections; renders catalog entries
// (grouped by category) once the /strategies query resolves; renders an error
// alert if the catalog request fails. Catalog comes from test/server.ts's default
// MSW handler.
import { screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'

import { server } from '../../test/server'
import { renderWithClient } from '../../test/utils'
import { AboutPage } from './AboutPage'

test('renders the page heading and methodology sections', async () => {
  renderWithClient(<AboutPage />)
  expect(
    await screen.findByRole('heading', { name: /about quantforge/i }),
  ).toBeInTheDocument()
  // Spot-check that the static methodology blocks made it onto the page.
  expect(screen.getByText(/Probability of Backtest Overfitting/i)).toBeInTheDocument()
  expect(screen.getByText(/Deflated Sharpe Ratio \(DSR\)/i)).toBeInTheDocument()
  expect(screen.getByText(/Walk-forward \+ Purged K-Fold CV/i)).toBeInTheDocument()
})

test('renders catalog strategies grouped by category once /strategies resolves', async () => {
  renderWithClient(<AboutPage />)
  // Wait for the dynamic catalog list — the default test catalog includes SMA,
  // Momentum, Mean Reversion (one per category here for that fixture).
  await waitFor(() => {
    expect(screen.getByText('SMA Crossover')).toBeInTheDocument()
  })
  // Category headings (h4 inside the catalog section) come from groupByCategory's
  // canonical order.
  expect(screen.getByRole('heading', { name: 'Trend' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Mean Reversion' })).toBeInTheDocument()
})

test('surfaces a catalog error when /strategies fails', async () => {
  server.use(
    http.get('/api/v1/strategies', () => HttpResponse.json({}, { status: 500 })),
  )
  renderWithClient(<AboutPage />)
  await waitFor(() => {
    expect(screen.getByRole('alert')).toHaveTextContent(/could not load the catalog/i)
  })
})
