import { useMutation } from '@tanstack/react-query'

import { requestBacktest } from '../../services/backtest'
import type { BacktestRequest } from '../../types/backtest'

// Backtests run on demand against a chosen config -> a mutation, not a cached query.
export function useBacktest() {
  return useMutation({
    mutationFn: (body: BacktestRequest) => requestBacktest(body),
  })
}
