// BacktestResultView: renders strategy/symbol heading + metrics + equity curve;
// positive total_return uses the .pass class chrome, negative uses .fail.
import { render, screen } from '@testing-library/react'

import type { BacktestResponse } from '../../types/backtest'
import { BacktestResultView } from './BacktestResultView'

const winning: BacktestResponse = {
  symbol: 'AAPL',
  strategy_name: 'sma_crossover',
  parameters: { fast: 5, slow: 20 },
  n_trades: 12,
  cost_rate: 0.001,
  metrics: {
    sharpe: 1.5,
    max_drawdown: -0.15,
    total_return: 0.42,
    annualized_return: 0.18,
    annualized_vol: 0.12,
  },
  equity_curve: [
    { timestamp_utc: '2024-01-01T00:00:00Z', equity: 100_000 },
    { timestamp_utc: '2024-12-01T00:00:00Z', equity: 142_000 },
  ],
}

const losing: BacktestResponse = {
  ...winning,
  metrics: { ...winning.metrics, total_return: -0.21 },
}

test('renders the heading, the metrics, and the equity curve summary', () => {
  render(<BacktestResultView result={winning} />)
  expect(screen.getByRole('heading')).toHaveTextContent(/sma_crossover/i)
  expect(screen.getByText('1.50')).toBeInTheDocument() // sharpe
  expect(screen.getByText('18.0%')).toBeInTheDocument() // annualized_return
  expect(screen.getByRole('status')).toHaveTextContent(/total return 42\.0%/i)
  expect(screen.getByLabelText('equity curve')).toBeInTheDocument()
})

test('uses the failing chrome for a negative total return', () => {
  const { container } = render(<BacktestResultView result={losing} />)
  expect(container.querySelector('.report.fail')).toBeInTheDocument()
})
