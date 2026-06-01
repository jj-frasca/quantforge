// App: renders the shell + page nav; default page is Validation; switching to
// Data Explorer renders the ingest form. Backend mocked with MSW.
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import App from './App'
import { server } from './test/server'
import { passingReport, renderWithClient } from './test/utils'

test('renders the app shell with the validation page by default', () => {
  renderWithClient(<App />)
  expect(screen.getByRole('heading', { name: /quantforge/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /run validation/i })).toBeInTheDocument()
  expect(
    screen.getByRole('button', { name: 'Validation', current: 'page' }),
  ).toBeInTheDocument()
})

test('runs validation and renders the report', async () => {
  server.use(http.post('/api/v1/validate', () => HttpResponse.json(passingReport)))
  renderWithClient(<App />)
  await userEvent.click(screen.getByRole('button', { name: /run validation/i }))
  expect(await screen.findByRole('status')).toHaveTextContent(/passes validation/i)
})

test('shows an error message when validation fails', async () => {
  server.use(http.post('/api/v1/validate', () => HttpResponse.json({}, { status: 500 })))
  renderWithClient(<App />)
  await userEvent.click(screen.getByRole('button', { name: /run validation/i }))
  expect(await screen.findByRole('alert')).toHaveTextContent(/failed/i)
})

test('switches to the Data Explorer page from the nav', async () => {
  renderWithClient(<App />)
  await userEvent.click(screen.getByRole('button', { name: 'Data Explorer' }))
  expect(screen.getByRole('button', { name: /ingest data/i })).toBeInTheDocument()
  expect(
    screen.getByRole('button', { name: 'Data Explorer', current: 'page' }),
  ).toBeInTheDocument()
})
