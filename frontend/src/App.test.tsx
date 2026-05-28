import { render, screen } from '@testing-library/react'

import App from './App'

test('renders the QuantForge app shell', () => {
  render(<App />)
  expect(screen.getByRole('heading', { name: /quantforge/i })).toBeInTheDocument()
})
