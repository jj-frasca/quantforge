// CompareSpreadCallout: renders one short sentence above the metrics table that
// makes the in-sample parameter-sensitivity story explicit — high Sharpe spread
// across configs is a strong signal of overfitting risk (which PBO will quantify
// on the Validation page). It does not duplicate the table; it interprets it.
import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import type { BacktestResponse } from '../../types/backtest'
import { CompareSpreadCallout } from './CompareSpreadCallout'
import type { CompareRow } from './useCompareBacktests'

const successWithSharpe = (sharpe: number): CompareRow => ({
  status: 'success',
  data: {
    symbol: 'AAPL',
    strategy_name: 'sma_crossover',
    parameters: { fast: 20, slow: 50 },
    n_trades: 0,
    cost_rate: 0,
    metrics: {
      sharpe,
      max_drawdown: -0.1,
      total_return: 0.1,
      annualized_return: 0.05,
      annualized_vol: 0.08,
    },
    equity_curve: [],
    buy_and_hold_curve: [],
    buy_and_hold_total_return: 0,
    drawdown_curve: [],
    rolling_sharpe_curve: [],
    rolling_sharpe_window: 60,
    return_distribution: { bins: [], skewness: 0, kurtosis: 0 },
    trade_markers: [],
  } as BacktestResponse,
})

const failure: CompareRow = { status: 'error', error: new Error('failed') }

test('renders nothing when fewer than 2 successful results — no spread to describe', () => {
  // 1 row is just a backtest; spread is undefined. Renders nothing so we don't
  // print a misleading "Sharpe spread: 0.00" callout that suggests stability.
  const { container } = render(
    <CompareSpreadCallout results={[successWithSharpe(0.9), failure]} />,
  )
  expect(container.firstChild).toBeNull()
})

test('renders the min/max Sharpe and spread for >= 2 successful rows', () => {
  render(
    <CompareSpreadCallout
      results={[
        successWithSharpe(0.3),
        successWithSharpe(1.2),
        successWithSharpe(0.6),
      ]}
    />,
  )
  const callout = screen.getByRole('region', { name: /sharpe spread/i })
  expect(callout).toHaveTextContent(/0\.30/)
  expect(callout).toHaveTextContent(/1\.20/)
  // Spread = max - min = 0.90 → user-readable.
  expect(callout).toHaveTextContent(/0\.90/)
})

test('flags a wide spread as a parameter-sensitivity signal', () => {
  // Threshold-driven copy: a spread of >= 0.5 in Sharpe is large enough that
  // the "parameter sensitivity" framing belongs on screen — it tells the user
  // what PBO on the next page is actually answering for them.
  render(
    <CompareSpreadCallout
      results={[successWithSharpe(0.2), successWithSharpe(1.0)]}
    />,
  )
  expect(screen.getByRole('region', { name: /sharpe spread/i })).toHaveTextContent(
    /parameter sensitivity/i,
  )
})

test('does NOT flag a narrow spread — stable configs are the boring good case', () => {
  // A spread of < 0.5 is small; flagging it would create noise. The methodology
  // hook is for the wide-spread case.
  render(
    <CompareSpreadCallout
      results={[successWithSharpe(0.85), successWithSharpe(1.05)]}
    />,
  )
  expect(
    screen.queryByText(/parameter sensitivity/i),
  ).not.toBeInTheDocument()
})
