// useCompareBacktests: fan out N parallel POST /api/v1/backtest calls (ADR-011) via
// Promise.allSettled. Each row reports its own status — one row's failure does not
// poison the others. Status transitions: idle -> pending -> settled.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { expect, test } from 'vitest'

import { server } from '../../test/server'
import type { BacktestRequest } from '../../types/backtest'
import { useCompareBacktests } from './useCompareBacktests'

const wrapper = ({ children }: { children: ReactNode }) => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

const baseResponse = {
  symbol: 'SPY',
  strategy_name: 'sma_crossover',
  parameters: { fast: 20, slow: 50 },
  n_trades: 4,
  cost_rate: 0.001,
  metrics: {
    sharpe: 0.9,
    max_drawdown: -0.1,
    total_return: 0.15,
    annualized_return: 0.05,
    annualized_vol: 0.06,
  },
  equity_curve: [{ timestamp_utc: '2024-01-01T00:00:00Z', equity: 100_000 }],
  buy_and_hold_curve: [{ timestamp_utc: '2024-01-01T00:00:00Z', equity: 100_000 }],
  buy_and_hold_total_return: 0.1,
  drawdown_curve: [{ timestamp_utc: '2024-01-01T00:00:00Z', drawdown: 0 }],
  rolling_sharpe_curve: [{ timestamp_utc: '2024-01-01T00:00:00Z', sharpe: 0 }],
  rolling_sharpe_window: 60,
  return_distribution: {
    bins: [{ bin_center: 0, frequency: 100 }],
    skewness: 0,
    kurtosis: 0,
  },
  trade_markers: [],
}

const buildRequest = (fast: number, slow: number): BacktestRequest => ({
  symbol: 'SPY',
  strategy: { name: 'sma', fast, slow },
  start_date: '2020-01-01T00:00:00Z',
  end_date: '2024-01-01T00:00:00Z',
  initial_capital: 100_000,
  cost_rate: 0.001,
})

test('starts idle with no results', () => {
  const { result } = renderHook(() => useCompareBacktests(), { wrapper })
  expect(result.current.status).toBe('idle')
  expect(result.current.results).toEqual([])
})

test('fans out N parallel calls and reports each row as success when all resolve', async () => {
  const seen: BacktestRequest[] = []
  server.use(
    http.post('/api/v1/backtest', async ({ request }) => {
      seen.push((await request.json()) as BacktestRequest)
      return HttpResponse.json(baseResponse)
    }),
  )

  const { result } = renderHook(() => useCompareBacktests(), { wrapper })
  await act(async () => {
    await result.current.submit([
      buildRequest(10, 50),
      buildRequest(20, 100),
      buildRequest(50, 200),
    ])
  })

  expect(result.current.status).toBe('settled')
  expect(result.current.results).toHaveLength(3)
  for (const row of result.current.results) {
    expect(row.status).toBe('success')
    // Narrow the discriminated union before reading the success-only `data`.
    if (row.status === 'success') expect(row.data.symbol).toBe('SPY')
  }
  // All three got dispatched; we don't constrain the order since they fan out concurrently.
  expect(seen).toHaveLength(3)
  const slowParams = seen.map((r) => r.strategy.slow as number).sort((a, b) => a - b)
  expect(slowParams).toEqual([50, 100, 200])
})

test('one row failing does not poison the others — per-row error reporting', async () => {
  // First call fails 422, the rest succeed. The hook must report row 0 as error
  // and rows 1/2 as success — this is the whole "per-row error handling" promise
  // in ADR-011 §Decision.
  let callIndex = 0
  server.use(
    http.post('/api/v1/backtest', () => {
      const index = callIndex++
      if (index === 0) {
        return HttpResponse.json({ detail: 'insufficient data' }, { status: 422 })
      }
      return HttpResponse.json(baseResponse)
    }),
  )

  const { result } = renderHook(() => useCompareBacktests(), { wrapper })
  await act(async () => {
    await result.current.submit([
      buildRequest(10, 50),
      buildRequest(20, 100),
      buildRequest(50, 200),
    ])
  })

  await waitFor(() => expect(result.current.status).toBe('settled'))
  expect(result.current.results).toHaveLength(3)
  const row0 = result.current.results[0]
  expect(row0.status).toBe('error')
  // Narrow before reading the error-only `error` field.
  if (row0.status === 'error') expect(row0.error.message).toMatch(/insufficient data/i)
  expect(result.current.results[1].status).toBe('success')
  expect(result.current.results[2].status).toBe('success')
})
