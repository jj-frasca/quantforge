import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import App from './App'
import { server } from './test/server'
import { passingReport, renderWithClient } from './test/utils'

test('renders the app shell with a run button', () => {
  renderWithClient(<App />)
  expect(screen.getByRole('heading', { name: /quantforge/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /run validation/i })).toBeInTheDocument()
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
