// ValidationReportPage: form defaults render; submit sends the typed body the backend
// expects; success renders the report; failure surfaces the backend `detail`.
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import { server } from '../../test/server'
import { passingReport, renderWithClient } from '../../test/utils'
import { ValidationReportPage } from './ValidationReportPage'

test('renders the form with sensible defaults', () => {
  renderWithClient(<ValidationReportPage />)
  expect(screen.getByLabelText(/symbol/i)).toHaveValue('AAPL')
  expect(screen.getByLabelText(/strategy/i)).toHaveValue('sma')
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
  await userEvent.selectOptions(screen.getByLabelText(/strategy/i), 'momentum')
  await userEvent.click(screen.getByRole('button', { name: /run validation/i }))

  expect(await screen.findByRole('status')).toHaveTextContent(/passes validation/i)
  expect(body).toEqual({
    symbol: 'AAPL',
    strategy: 'momentum',
    start_date: '2020-01-01T00:00:00Z',
    end_date: '2024-01-01T00:00:00Z',
  })
})

test('surfaces the backend detail when validation fails', async () => {
  server.use(
    http.post('/api/v1/validate', () =>
      HttpResponse.json({ detail: 'insufficient data' }, { status: 422 }),
    ),
  )
  renderWithClient(<ValidationReportPage />)
  await userEvent.click(screen.getByRole('button', { name: /run validation/i }))
  await waitFor(() => {
    expect(screen.getByRole('alert')).toHaveTextContent(/insufficient data/i)
  })
})
