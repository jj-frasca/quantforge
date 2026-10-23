import { screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'

import { server } from '../../test/server'
import { renderWithClient } from '../../test/utils'
import { CrossSectionalPanel } from './CrossSectionalPanel'

const highMethod = 'restricted-pandas-3.0.6-cython-high-purged-equal-weight-continuation-v2'
const high = {
  method: highMethod, status: 'measured', n_bars: 1200, requested_folds: 3, floor: 0,
  reason: null, dependency_rule: 'rolling-high-v1', max_price_lag: 126, embargo: 126,
  kept_fold_ordinals: [0, 1, 2], mean_oos_sharpe: 0, mean_oos_hold_sharpe: -0.2,
}
const trial = {
  strategy_name: 'xs_52w_high', observed_sharpe: 0.5, deflated_sharpe: -0.1,
  pbo: 0.4, parameter_stability_score: 0.2, purged_cv_oos_sharpe: 0, purged_diagnostic: high,
}
const view = {
  created_at: '2026-10-22T10:00:00Z', universe_size: 20, graduated: false,
  trials: [trial, { ...trial, strategy_name: 'xs_reversal', purged_cv_oos_sharpe: -0.3,
    purged_diagnostic: { ...high, method: 'restricted-shift-family-purged-equal-weight-continuation-v1',
      dependency_rule: 'shifted-reversal-v1', max_price_lag: 4, embargo: 4, mean_oos_sharpe: -0.3 } }],
}

test('renders mixed-method means and qualifies trailing-high fold details without raw identifiers', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json(view)))
  renderWithClient(<CrossSectionalPanel />)
  const highRow = (await screen.findByRole('cell', { name: 'xs_52w_high' })).closest('tr')!
  const shiftRow = screen.getByRole('cell', { name: 'xs_reversal' }).closest('tr')!
  expect(within(highRow).getByText('0.00')).toBeInTheDocument()
  expect(within(shiftRow).getByText('-0.30')).toBeInTheDocument()
  expect(within(highRow).getByText(/same-kept-fold equal-weight universe benchmark: -0.20/i)).toBeInTheDocument()
  const details = highRow.querySelector('details')!
  expect(details).not.toHaveAttribute('open')
  expect(within(details).getByText(/pandas 3\.0\.6.*Cython.*trailing-high/i)).toBeInTheDocument()
  expect(within(details).getByText(/allocated price lag: 126.*embargo: 126/i)).toBeInTheDocument()
  expect(within(shiftRow).queryByText(/pandas 3\.0\.6/i)).not.toBeInTheDocument()
  expect(screen.queryByText(/restricted-pandas|rolling-high-v1|restricted-shift|shifted-reversal-v1/i)).not.toBeInTheDocument()
  expect(screen.getByText(/audited family recipes/i)).toBeInTheDocument()
  for (const caveat of [/later training is intentional/i, /winning family uses the complete search sample/i,
    /static snapshots, not historical point-in-time/i, /account entry and switching trades are not reconciled/i,
    /equal means of retained-fold Sharpes/i]) {
    expect(screen.getByText(caveat)).toBeInTheDocument()
  }
})

test('high no-fold evidence retains its engine qualification without inventing a benchmark', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json({ ...view, trials: [{ ...trial,
    purged_cv_oos_sharpe: null, purged_diagnostic: { ...high, status: 'no_usable_folds',
      n_bars: 300, max_price_lag: 252, embargo: 252, kept_fold_ordinals: [],
      mean_oos_sharpe: null, mean_oos_hold_sharpe: null } }] })))
  renderWithClient(<CrossSectionalPanel />)
  expect(await screen.findByText(/not measured · no usable folds/i)).toBeInTheDocument()
  expect(screen.getByText(/pandas 3\.0\.6.*Cython.*trailing-high/i)).toBeInTheDocument()
  expect(screen.getByText(/0 of 3 folds kept/i)).toBeInTheDocument()
  expect(screen.queryByText(/same-kept-fold equal-weight universe benchmark:/i)).not.toBeInTheDocument()
})

test('high measured negative mean remains a measured score with its paired control', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json({ ...view,
    trials: [{ ...trial, purged_cv_oos_sharpe: -0.7,
      purged_diagnostic: { ...high, mean_oos_sharpe: -0.7 } }],
  })))
  renderWithClient(<CrossSectionalPanel />)
  const row = (await screen.findByRole('cell', { name: 'xs_52w_high' })).closest('tr')!
  expect(within(row).getByText('-0.70')).toBeInTheDocument()
  expect(within(row).getByText(/same-kept-fold equal-weight universe benchmark: -0.20/i)).toBeInTheDocument()
  expect(within(row).queryByText(/no usable folds/i)).not.toBeInTheDocument()
})
