import { screen, waitForElementToBeRemoved } from '@testing-library/react'
import { http, HttpResponse } from 'msw'

import { server } from '../../test/server'
import { renderWithClient } from '../../test/utils'
import { EquityCurvePanel } from './EquityCurvePanel'

const curve = [
  {
    timestamp: '2026-08-01T00:00:00Z',
    equity: 100000.0,
    cash: 100000.0,
    n_positions: 0,
    return_since_start: 0.0,
  },
  {
    timestamp: '2026-08-05T02:07:04.170565Z',
    equity: 92488.99,
    cash: 60917.07,
    n_positions: 3,
    return_since_start: -0.0751101,
  },
]

test('renders the headline current equity and return since the $100k start', async () => {
  server.use(http.get('/api/v1/equity-curve', () => HttpResponse.json(curve)))
  renderWithClient(<EquityCurvePanel />)

  // Latest snapshot drives the headline — the honest "are we making money?" number.
  expect(await screen.findByText('$92,488.99')).toBeInTheDocument()
  expect(screen.getByText(/-7\.51% since \$100k start/)).toBeInTheDocument()
  // Latest values surface: cash + open positions + as-of date.
  expect(screen.getByText(/as of 2026-08-05 · cash \$60,917\.07 · 3 positions/)).toBeInTheDocument()
})

test('renders the empty state when no snapshot has been recorded', async () => {
  server.use(http.get('/api/v1/equity-curve', () => HttpResponse.json([])))
  renderWithClient(<EquityCurvePanel />)

  expect(await screen.findByText(/no equity snapshots yet/i)).toBeInTheDocument()
})

test('renders the single-point headline and defers the curve until a second snapshot', async () => {
  server.use(http.get('/api/v1/equity-curve', () => HttpResponse.json([curve[1]])))
  renderWithClient(<EquityCurvePanel />)

  expect(await screen.findByText('$92,488.99')).toBeInTheDocument()
  expect(screen.getByText(/renders once a second snapshot accrues/i)).toBeInTheDocument()
})

test('shows an error message when the equity-curve endpoint fails', async () => {
  server.use(http.get('/api/v1/equity-curve', () => new HttpResponse(null, { status: 500 })))
  renderWithClient(<EquityCurvePanel />)

  expect(await screen.findByText(/could not load the equity curve/i)).toBeInTheDocument()
})

test('shows a loading indicator while the equity curve is pending', async () => {
  server.use(http.get('/api/v1/equity-curve', () => HttpResponse.json(curve)))
  renderWithClient(<EquityCurvePanel />)

  await waitForElementToBeRemoved(() => screen.queryByText(/loading equity curve/i))
  expect(await screen.findByText('$92,488.99')).toBeInTheDocument()
})
