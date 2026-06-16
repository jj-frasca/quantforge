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
  buy_and_hold_curve: [
    { timestamp_utc: '2024-01-01T00:00:00Z', equity: 100_000 },
    { timestamp_utc: '2024-12-01T00:00:00Z', equity: 120_000 },
  ],
  buy_and_hold_total_return: 0.2,
  drawdown_curve: [
    { timestamp_utc: '2024-01-01T00:00:00Z', drawdown: 0 },
    { timestamp_utc: '2024-06-01T00:00:00Z', drawdown: -0.15 },
    { timestamp_utc: '2024-12-01T00:00:00Z', drawdown: -0.05 },
  ],
  rolling_sharpe_curve: [
    { timestamp_utc: '2024-01-01T00:00:00Z', sharpe: 0 },
    { timestamp_utc: '2024-06-01T00:00:00Z', sharpe: 1.5 },
    { timestamp_utc: '2024-12-01T00:00:00Z', sharpe: 1.2 },
  ],
  rolling_sharpe_window: 60,
  return_distribution: {
    bins: [
      { bin_center: -0.01, frequency: 5 },
      { bin_center: 0.0, frequency: 200 },
      { bin_center: 0.01, frequency: 45 },
    ],
    skewness: -0.3,
    kurtosis: 1.4,
  },
  trade_markers: [
    { timestamp_utc: '2024-03-15T00:00:00Z', direction: 'buy', equity: 110_000 },
    { timestamp_utc: '2024-07-22T00:00:00Z', direction: 'sell', equity: 125_000 },
    { timestamp_utc: '2024-09-10T00:00:00Z', direction: 'buy', equity: 120_000 },
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
  expect(screen.getByRole('status')).toHaveTextContent(/buy & hold 20\.0%/i)
  expect(screen.getByLabelText('equity curve')).toBeInTheDocument()
})

test('uses the failing chrome for a negative total return', () => {
  const { container } = render(<BacktestResultView result={losing} />)
  expect(container.querySelector('.report.fail')).toBeInTheDocument()
})

test('renders plain-English hints under each headline metric so a non-quant can read them', () => {
  // The "democratize advanced trading" rule: a metric without context is hostile to
  // anyone who hasn't memorized the textbook. We assert at least the Sharpe and Max
  // drawdown hints so the panel can't ship without them; the others wear the same
  // pattern and are covered by the visual diff.
  render(<BacktestResultView result={winning} />)
  expect(screen.getByText(/return per unit of risk/i)).toBeInTheDocument()
  expect(screen.getByText(/worst peak-to-trough drop/i)).toBeInTheDocument()
})
