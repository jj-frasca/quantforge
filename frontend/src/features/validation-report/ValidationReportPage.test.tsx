// ValidationReportPage: form renders once the catalog lands (async); submit sends the
// typed body the backend expects; success renders the report; failure surfaces the
// backend `detail`. Catalog comes from the test/server.ts default handler.
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach } from 'vitest'

import { useAppShell } from '../../state/appShell'
import { server } from '../../test/server'
import { passingReport, renderWithClient } from '../../test/utils'
import { ValidationReportPage } from './ValidationReportPage'

beforeEach(() => {
  // Reset appShell — Validation page consumes pendingValidation on mount.
  useAppShell.setState({ activePage: 'data-explorer', pendingValidation: null })
})

test('renders the form with sensible defaults once the catalog lands', async () => {
  renderWithClient(<ValidationReportPage />)
  expect(await screen.findByLabelText(/symbol/i)).toHaveValue('AAPL')
  expect(screen.getByLabelText(/^strategy$/i)).toHaveValue('sma')
  expect(screen.getByRole('button', { name: /run validation/i })).toBeEnabled()
})

test('submitting sends the typed body and renders the report on success', async () => {
  let body: unknown
  server.use(
    http.post('/api/v1/validate', async ({ request }) => {
      body = await request.json()
      return HttpResponse.json(passingReport)
    }),
  )

  renderWithClient(<ValidationReportPage />)
  // Wait for the catalog-driven dropdown to populate before selecting.
  await waitFor(() => {
    expect(screen.getByLabelText(/^strategy$/i)).not.toHaveValue('')
  })
  await userEvent.selectOptions(screen.getByLabelText(/^strategy$/i), 'momentum')
  await userEvent.click(screen.getByRole('button', { name: /run validation/i }))

  expect(await screen.findByRole('status')).toHaveTextContent(/passes validation/i)
  // Dates come from defaultDateRange(5) anchored to "today" — covered by
  // defaultDateRange.test.ts; here we just assert the rest of the body and the shape
  // of the date fields.
  expect(body).toMatchObject({
    symbol: 'AAPL',
    strategy: 'momentum',
  })
  const dateRe = /^\d{4}-\d{2}-\d{2}T00:00:00Z$/
  const wireBody = body as { start_date: string; end_date: string }
  expect(wireBody.start_date).toMatch(dateRe)
  expect(wireBody.end_date).toMatch(dateRe)
})

test('the catalog drives the strategy dropdown — new strategies appear automatically', async () => {
  // Regression for the bug where ValidationReportPage hardcoded the original three
  // names and silently dropped every new catalog entry. After ADR-010 §Consequences
  // extends /validate to the full catalog, every catalog option must be reachable.
  renderWithClient(<ValidationReportPage />)
  // Wait for options to populate (catalog is async).
  await waitFor(() => {
    const dropdown = screen.getByLabelText(/^strategy$/i)
    expect(dropdown.querySelectorAll('option').length).toBeGreaterThan(1)
  })
  const dropdown = screen.getByLabelText(/^strategy$/i)
  const optionValues = Array.from(dropdown.querySelectorAll('option')).map((o) => o.value)
  // The default test catalog (test/server.ts) includes mean_reversion among others.
  expect(optionValues).toContain('mean_reversion')
})

test('hydrates the form from a pending validation handoff on mount', async () => {
  // The methodology bridge from Compare Configs: clicking "Validate this config"
  // sets appShell.pendingValidation AND switches the page. ValidationReportPage
  // must consume that handoff on mount, pre-fill the form, and clear the store —
  // single-shot so re-navigating doesn't re-apply.
  useAppShell.setState({
    pendingValidation: {
      symbol: 'QQQ',
      strategy: 'mean_reversion',
      startDate: '2020-01-01',
      endDate: '2024-12-31',
    },
  })
  renderWithClient(<ValidationReportPage />)
  expect(await screen.findByLabelText(/symbol/i)).toHaveValue('QQQ')
  expect(screen.getByLabelText(/^strategy$/i)).toHaveValue('mean_reversion')
  expect(screen.getByLabelText(/start date/i)).toHaveValue('2020-01-01')
  expect(screen.getByLabelText(/end date/i)).toHaveValue('2024-12-31')
  // Store is cleared post-consumption so re-mounts don't re-apply.
  expect(useAppShell.getState().pendingValidation).toBeNull()
})

test('surfaces the backend detail when validation fails', async () => {
  server.use(
    http.post('/api/v1/validate', () =>
      HttpResponse.json({ detail: 'insufficient data' }, { status: 422 }),
    ),
  )
  renderWithClient(<ValidationReportPage />)
  await screen.findByLabelText(/^strategy$/i)
  await userEvent.click(screen.getByRole('button', { name: /run validation/i }))
  await waitFor(() => {
    expect(screen.getByRole('alert')).toHaveTextContent(/insufficient data/i)
  })
})
