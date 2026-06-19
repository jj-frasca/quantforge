// CompareMetricsTable: per-row metrics + a "Validate this config" button on each
// SUCCESSFUL row that hands off the (symbol, strategy, dates) to the Validation
// page via the appShell store. The button is the methodology bridge — Compare
// shows parameter-sensitivity in-sample; Validation answers whether the best
// config survives the out-of-sample penalty (PBO + Deflated Sharpe).
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, test, vi } from 'vitest'

import { useAppShell, type ValidationHandoff } from '../../state/appShell'
import type { BacktestResponse } from '../../types/backtest'
import { CompareMetricsTable } from './CompareMetricsTable'
import type { CompareRow } from './useCompareBacktests'

const handoffBase: Omit<ValidationHandoff, 'symbol' | 'strategy'> = {
  startDate: '2020-01-01',
  endDate: '2024-01-01',
}

const success = (sharpe: number): CompareRow => ({
  status: 'success',
  data: {
    symbol: 'AAPL',
    strategy_name: 'sma_crossover',
    parameters: { fast: 20, slow: 50 },
    n_trades: 3,
    cost_rate: 0.001,
    metrics: {
      sharpe,
      max_drawdown: -0.1,
      total_return: 0.2,
      annualized_return: 0.05,
      annualized_vol: 0.08,
    },
    equity_curve: [],
    buy_and_hold_curve: [],
    buy_and_hold_total_return: 0.1,
    drawdown_curve: [],
    rolling_sharpe_curve: [],
    rolling_sharpe_window: 60,
    return_distribution: { bins: [], skewness: 0, kurtosis: 0 },
    trade_markers: [],
  } as BacktestResponse,
})

const failure: CompareRow = { status: 'error', error: new Error('insufficient data') }

beforeEach(() => {
  useAppShell.setState({ activePage: 'data-explorer', pendingValidation: null })
})

test('renders a Validate button on every successful row', () => {
  render(
    <CompareMetricsTable
      symbol="AAPL"
      strategy="sma"
      startDate="2020-01-01"
      endDate="2024-01-01"
      rows={[
        { label: 'Config A', values: { fast: 10, slow: 50 } },
        { label: 'Config B', values: { fast: 20, slow: 100 } },
      ]}
      results={[success(0.9), success(1.1)]}
    />,
  )
  const buttons = screen.getAllByRole('button', { name: /validate this config/i })
  expect(buttons).toHaveLength(2)
})

test('does NOT render a Validate button on failed rows — no config to validate', () => {
  // A row whose backtest failed has no meaningful Sharpe to compare to PBO;
  // offering Validate on it would just chain another failure.
  render(
    <CompareMetricsTable
      symbol="AAPL"
      strategy="sma"
      startDate="2020-01-01"
      endDate="2024-01-01"
      rows={[
        { label: 'Config A', values: { fast: 10, slow: 50 } },
        { label: 'Config B', values: { fast: 20, slow: 100 } },
      ]}
      results={[failure, success(0.9)]}
    />,
  )
  const buttons = screen.getAllByRole('button', { name: /validate this config/i })
  expect(buttons).toHaveLength(1)
})

test('clicking Validate stores the handoff and switches the active page', async () => {
  const requestSpy = vi.spyOn(useAppShell.getState(), 'requestValidation')
  // Spy doesn't intercept the actual store — that's the bound function on the
  // initial state object. We can either rebind or just read the post-click state.
  requestSpy.mockRestore()

  render(
    <CompareMetricsTable
      symbol="SPY"
      strategy="sma"
      startDate="2020-01-01"
      endDate="2024-01-01"
      rows={[
        { label: 'Config A', values: { fast: 10, slow: 50 } },
        { label: 'Config B', values: { fast: 50, slow: 200 } },
      ]}
      results={[success(0.9), success(1.4)]}
    />,
  )

  await userEvent.click(screen.getAllByRole('button', { name: /validate this config/i })[1])

  const state = useAppShell.getState()
  expect(state.activePage).toBe('validation')
  expect(state.pendingValidation).toEqual({
    symbol: 'SPY',
    strategy: 'sma',
    ...handoffBase,
  })
})
