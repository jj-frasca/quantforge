import { useCallback, useState } from 'react'

import { requestBacktest } from '../../services/backtest'
import type { BacktestRequest, BacktestResponse } from '../../types/backtest'

// ADR-011 §Decision: Compare-configs fans out N parallel POST /backtest calls via
// Promise.allSettled. Per-row error handling is the explicit promise — one row
// failing must not poison the others. This hook is the only place the fan-out
// concept lives; components below it see a flat list of per-row statuses.

export type CompareRow =
  | { status: 'success'; data: BacktestResponse }
  | { status: 'error'; error: Error }

export type CompareStatus = 'idle' | 'pending' | 'settled'

interface State {
  status: CompareStatus
  results: CompareRow[]
}

export interface UseCompareBacktestsResult extends State {
  submit: (requests: BacktestRequest[]) => Promise<void>
}

export function useCompareBacktests(): UseCompareBacktestsResult {
  const [state, setState] = useState<State>({ status: 'idle', results: [] })

  const submit = useCallback(async (requests: BacktestRequest[]) => {
    setState({ status: 'pending', results: [] })
    const settled = await Promise.allSettled(requests.map((r) => requestBacktest(r)))
    const results: CompareRow[] = settled.map((s) =>
      s.status === 'fulfilled'
        ? { status: 'success', data: s.value }
        : {
            status: 'error',
            error: s.reason instanceof Error ? s.reason : new Error(String(s.reason)),
          },
    )
    setState({ status: 'settled', results })
  }, [])

  return { ...state, submit }
}
