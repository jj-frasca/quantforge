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
  interpretations: [
    { metric: 'pbo', message: 'PBO 20% — overfitting risk is low.', verdict: 'good' },
    {
      metric: 'deflated_sharpe',
      message: 'Deflated Sharpe 0.40 — survives the multiple-testing penalty.',
      verdict: 'good',
    },
    {
      metric: 'parameter_stability_score',
      message: 'Parameter stability 85% — robust.',
      verdict: 'good',
    },
  ],
  passed: true,
  regime_breakdown: {
    bull: { n_bars: 180, total_return: 0.15, sharpe: 1.3 },
    bear: { n_bars: 100, total_return: 0.05, sharpe: 0.9 },
  },
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
  interpretations: [
    {
      metric: 'pbo',
      message: 'PBO 89% — high probability the strategy is overfit.',
      verdict: 'bad',
    },
    {
      metric: 'deflated_sharpe',
      message: "Deflated Sharpe -0.30 — plausibly attributable to luck.",
      verdict: 'bad',
    },
    {
      metric: 'parameter_stability_score',
      message: 'Parameter stability 30% — high model fragility.',
      verdict: 'bad',
    },
  ],
  passed: false,
  regime_breakdown: {
    bull: { n_bars: 220, total_return: 0.12, sharpe: 1.1 },
    bear: { n_bars: 60, total_return: -0.18, sharpe: -0.5 },
  },
}
