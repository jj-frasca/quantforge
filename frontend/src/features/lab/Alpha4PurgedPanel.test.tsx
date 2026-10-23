import { screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'

import { server } from '../../test/server'
import { renderWithClient } from '../../test/utils'
import { CrossSectionalPanel } from './CrossSectionalPanel'

const evidence = {
  method: 'restricted-pandas-3.0.6-numpy-2.5.4-cython-alpha4-purged-equal-weight-continuation-v4',
  status: 'measured', reason: null, n_bars: 1200, requested_folds: 3, floor: 0,
  dependency_rule: 'rolling-alpha4-percentile-v1', max_price_lag: 21, embargo: 21,
  kept_fold_ordinals: [0, 1, 2], mean_oos_sharpe: 0, mean_oos_hold_sharpe: -0.2,
}
const trial = { strategy_name: 'xs_alpha4', observed_sharpe: 0.5, deflated_sharpe: -0.1,
  pbo: 0.4, parameter_stability_score: 0.2, purged_cv_oos_sharpe: 0, purged_diagnostic: evidence }
const view = { created_at: '2026-10-22T10:00:00Z', universe_size: 20, graduated: false,
  trials: [trial, { ...trial, strategy_name: 'xs_52w_high',
    purged_diagnostic: { ...evidence,
      method: 'restricted-pandas-3.0.6-cython-high-purged-equal-weight-continuation-v2',
      dependency_rule: 'rolling-high-v1', max_price_lag: 126, embargo: 126 } },
  { ...trial, strategy_name: 'xs_reversal', purged_diagnostic: { ...evidence,
    method: 'restricted-shift-family-purged-equal-weight-continuation-v1',
    dependency_rule: 'shifted-reversal-v1', max_price_lag: 4, embargo: 4 } },
  { ...trial, strategy_name: 'xs_alpha9', purged_diagnostic: { ...evidence,
    method: 'restricted-pandas-3.0.6-cython-alpha9-purged-equal-weight-continuation-v3',
    dependency_rule: 'rolling-alpha9-v1', max_price_lag: 11, embargo: 11 } }],
}

test.each([0, -0.7])('renders mixed Alpha4 measured %s with qualified fold evidence and distinct recipes', async (mean) => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json({ ...view,
    trials: [{ ...trial, purged_cv_oos_sharpe: mean,
      purged_diagnostic: { ...evidence, mean_oos_sharpe: mean } }, ...view.trials.slice(1)],
  })))
  renderWithClient(<CrossSectionalPanel />)
  const row = (await screen.findByRole('cell', { name: 'xs_alpha4' })).closest('tr')!
  expect(within(row).getByText(mean.toFixed(2))).toBeInTheDocument()
  expect(within(row).getByText(/same-kept-fold equal-weight universe benchmark: -0.20/i)).toBeInTheDocument()
  const details = row.querySelector('details')!
  expect(details).not.toHaveAttribute('open')
  expect(within(details).getByText(/pandas 3\.0\.6.*Cython.*NumPy 2\.5\.4.*window-percentile/i)).toBeInTheDocument()
  expect(within(details).getByText(/allocated price lag: 21.*embargo: 21/i)).toBeInTheDocument()
  expect(screen.getByText(/pandas 3\.0\.6.*Cython.*trailing-high/i)).toBeInTheDocument()
  expect(screen.getByText(/pandas 3\.0\.6.*Cython.*price-change-extrema/i)).toBeInTheDocument()
  const caption = screen.getByText(/Purged CV support is restricted/i)
  // ADR-353 adopts the producer; support copy now names its reviewed runtime.
  expect(caption).toHaveTextContent(/Alpha4 window-percentile recipes restricted to pandas 3\.0\.6 Cython and NumPy 2\.5\.4/i)
  expect(screen.getByText('no graduate')).toBeInTheDocument()
  expect(screen.queryByText(/restricted-pandas|rolling-alpha4-percentile-v1|rolling-high-v1|shifted-reversal-v1/i)).not.toBeInTheDocument()
  for (const caveat of [/later training is intentional/i, /winning family uses the complete search sample/i,
    /static snapshots, not historical point-in-time/i, /account entry and switching trades are not reconciled/i,
    /equal means of retained-fold Sharpes/i]) expect(screen.getByText(caveat)).toBeInTheDocument()
})

test.each([null, undefined])('historical Alpha4 remains unpaired without recipe attribution %s', async (absent) => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json({ ...view,
    trials: [{ ...trial, purged_cv_oos_sharpe: -0.7, purged_diagnostic: absent }],
  })))
  renderWithClient(<CrossSectionalPanel />)
  expect(await screen.findByText('-0.70 · legacy, unpaired')).toBeInTheDocument()
  // Historical rows still receive no invented runtime or fold qualification.
  const row = screen.getByRole('cell', { name: 'xs_alpha4' }).closest('tr')!
  expect(within(row).queryByText(/window-percentile|pandas|NumPy/i)).not.toBeInTheDocument()
  expect(screen.queryByText('Fold evidence')).not.toBeInTheDocument()
  expect(screen.queryByText(/same-kept-fold equal-weight universe benchmark:/i)).not.toBeInTheDocument()
})

test('malformed Alpha4 lag reaches the existing request error state', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json({ ...view,
    trials: [{ ...trial, purged_diagnostic: { ...evidence, max_price_lag: 6, embargo: 6 } }],
  })))
  renderWithClient(<CrossSectionalPanel />)
  expect(await screen.findByRole('alert')).toHaveTextContent(/Could not load the cross-sectional hunt/i)
  expect(screen.queryByRole('cell', { name: 'xs_alpha4' })).not.toBeInTheDocument()
})

test('Alpha4 no-fold outcome retains qualification without fabricated score or benchmark', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json({ ...view,
    trials: [{ ...trial, purged_cv_oos_sharpe: null, purged_diagnostic: { ...evidence,
      n_bars: 12, status: 'no_usable_folds', kept_fold_ordinals: [],
      mean_oos_sharpe: null, mean_oos_hold_sharpe: null } }],
  })))
  renderWithClient(<CrossSectionalPanel />)
  expect(await screen.findByText(/not measured · no usable folds/i)).toBeInTheDocument()
  expect(screen.getByText(/pandas 3\.0\.6.*Cython.*NumPy 2\.5\.4.*window-percentile/i)).toBeInTheDocument()
  expect(screen.getByText(/0 of 3 folds kept/i)).toBeInTheDocument()
  expect(screen.queryByText(/same-kept-fold equal-weight universe benchmark:/i)).not.toBeInTheDocument()
})
