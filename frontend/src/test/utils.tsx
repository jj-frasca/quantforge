import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactElement } from 'react'

import type { ValidationReport } from '../types/validation'

export function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

export const passingReport: ValidationReport = {
  strategy_name: 'sma',
  observed_sharpe: 1.2,
  deflated_sharpe: 0.4,
  pbo: 0.2,
  parameter_stability_score: 0.85,
  n_walk_forward_splits: 5,
  n_purged_folds: 5,
  flags: [],
  passed: true,
}

export const failingReport: ValidationReport = {
  strategy_name: 'sma',
  observed_sharpe: 0.1,
  deflated_sharpe: -0.3,
  pbo: 0.89,
  parameter_stability_score: 0.3,
  n_walk_forward_splits: 5,
  n_purged_folds: 5,
  flags: ['high overfitting risk (PBO >= 0.5)'],
  passed: false,
}
