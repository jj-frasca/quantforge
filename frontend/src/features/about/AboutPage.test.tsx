// AboutPage: renders the static methodology sections; renders catalog entries
// (grouped by category) once the /strategies query resolves; renders an error
// alert if the catalog request fails. Catalog comes from test/server.ts's default
// MSW handler.
import { screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'

import { defaultStrategyCatalog, server } from '../../test/server'
import { renderWithClient } from '../../test/utils'
import { AboutPage } from './AboutPage'

test('renders the page heading and methodology sections', async () => {
  renderWithClient(<AboutPage />)
  expect(
    await screen.findByRole('heading', { name: /about quantforge/i }),
  ).toBeInTheDocument()
  // Spot-check that the static methodology blocks made it onto the page.
  expect(screen.getByText(/Probability of Backtest Overfitting/i)).toBeInTheDocument()
  // ADR-054: the glossary must name the statistic it actually shows — a margin, not the paper's
  // probability-form DSR.
  expect(screen.getByText(/Selection-adjusted Sharpe margin/i)).toBeInTheDocument()
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

test('renders a strategy entry\'s citations when the catalog provides them', async () => {
  // The default catalog's entries all have empty `citations` arrays (mirrors
  // production's mostly-uncited strategies), so the `citations.length > 0`
  // branch needs its own override to exercise.
  server.use(
    http.get('/api/v1/strategies', () =>
      HttpResponse.json([
        {
          ...defaultStrategyCatalog[0],
          citations: ['Lo & MacKinlay (1990)', 'Moskowitz et al. (2012)'],
        },
        ...defaultStrategyCatalog.slice(1),
      ]),
    ),
  )
  renderWithClient(<AboutPage />)
  expect(await screen.findByText('Lo & MacKinlay (1990)')).toBeInTheDocument()
  expect(screen.getByText('Moskowitz et al. (2012)')).toBeInTheDocument()
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

test('explains observation-based PBO ranks and ties without promising a null value', async () => {
  renderWithClient(<AboutPage />)
  await screen.findByText('SMA Crossover')
  const methodology = screen.getByRole('region', { name: 'validation methodology' })
  const pbo = within(methodology).getByText(/balanced splits of time observations/i)
  expect(pbo).toHaveTextContent(/in-sample winners.*out-of-sample median/i)
  expect(pbo).toHaveTextContent(/tied in-sample winners contribute equally/i)
  expect(pbo).toHaveTextContent(/≥ 0\.5.*high overfitting risk/i)
  expect(pbo).toHaveTextContent(/no universal null PBO value/i)
  expect(methodology).not.toHaveTextContent(/split of the configuration grid/i)
  expect(methodology).not.toHaveTextContent(/random strategy yields/i)
  // Preserve the other headline threshold while correcting interpretation only.
  expect(methodology).toHaveTextContent(/margin ≤ 0/)
  expect(methodology).toHaveTextContent(/> 0 is the "survives multiple testing" threshold/)
})

test('distinguishes continuation-window scores from switching-account returns', async () => {
  renderWithClient(<AboutPage />)
  await screen.findByText('SMA Crossover')
  const methodology = screen.getByRole('region', { name: 'validation methodology' })
  expect(methodology).toHaveTextContent(/walk-forward selects using earlier training rows/i)
  expect(methodology).toHaveTextContent(/continued fixed-config paths/i)
  expect(methodology).toHaveTextContent(/equal mean of window Sharpes/i)
  expect(methodology).toHaveTextContent(/does not reconcile entry or switching trades for one account/i)
})

test('reports purged resampling as noncausal with a proxy gap and limited isolation', async () => {
  renderWithClient(<AboutPage />)
  await screen.findByText('SMA Crossover')
  const methodology = screen.getByRole('region', { name: 'validation methodology' })
  expect(methodology).toHaveTextContent(/lookback-based proxy gap on both sides/i)
  expect(methodology).toHaveTextContent(/training can include observations after the test block/i)
  expect(methodology).toHaveTextContent(/not a live-simulation estimate/i)
  expect(methodology).toHaveTextContent(/does not guarantee independence/i)
  expect(methodology).not.toHaveTextContent(/prevent look-ahead leakage/i)
})

test('keeps paper-only scope explicit without stale check counts or fixed null claims', async () => {
  renderWithClient(<AboutPage />)
  await screen.findByText('SMA Crossover')
  const capabilities = screen.getByRole('region', { name: 'what you can do' })
  expect(capabilities).toHaveTextContent(/data quality engine/i)
  expect(capabilities).not.toHaveTextContent(/6-check/i)
  const scope = screen.getByRole('region', { name: 'scope honesty' })
  expect(scope).toHaveTextContent(/no real money ever moves/i)
  expect(scope).toHaveTextContent(/null calibration depends on the search, candidate dependence and ties/i)
  expect(scope).not.toHaveTextContent(/random walk gives PBO/i)
  expect(screen.getByRole('link', { name: 'ADR-001 — Monorepo + scope' })).toHaveAttribute(
    'href',
    'https://github.com/jj-frasca/quantforge/blob/master/docs/adr/ADR-001-monorepo-and-scope.md',
  )
})
