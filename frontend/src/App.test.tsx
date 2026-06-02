// App: renders the shell + 3-page nav; default page is Data Explorer (natural flow:
// ingest first, then backtest or validate). Backend mocked with MSW.
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import App from './App'
import { server } from './test/server'
import { passingReport, renderWithClient } from './test/utils'

test('renders the app shell with the Data Explorer page by default', () => {
  renderWithClient(<App />)
  expect(screen.getByRole('heading', { name: /quantforge/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /ingest data/i })).toBeInTheDocument()
  expect(
    screen.getByRole('button', { name: 'Data Explorer', current: 'page' }),
  ).toBeInTheDocument()
})

test('switches to Validation and runs the suite', async () => {
  server.use(http.post('/api/v1/validate', () => HttpResponse.json(passingReport)))
  renderWithClient(<App />)
  await userEvent.click(screen.getByRole('button', { name: 'Validation' }))
  await userEvent.click(screen.getByRole('button', { name: /run validation/i }))
  expect(await screen.findByRole('status')).toHaveTextContent(/passes validation/i)
})

test('switches to Backtest Results from the nav', async () => {
  renderWithClient(<App />)
  await userEvent.click(screen.getByRole('button', { name: 'Backtest Results' }))
  expect(screen.getByRole('button', { name: /run backtest/i })).toBeInTheDocument()
  expect(
    screen.getByRole('button', { name: 'Backtest Results', current: 'page' }),
  ).toBeInTheDocument()
})
