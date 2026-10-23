import { screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'

import { server } from '../../test/server'
import { renderWithClient } from '../../test/utils'
import { CrossSectionalPanel } from './CrossSectionalPanel'

const v1 = 'restricted-shift-family-purged-equal-weight-continuation-v1'
const v2 = 'restricted-pandas-3.0.6-cython-high-purged-equal-weight-continuation-v2'
const v3 = 'restricted-pandas-3.0.6-cython-alpha9-purged-equal-weight-continuation-v3'
const v4 = 'restricted-pandas-3.0.6-numpy-2.5.4-cython-alpha4-purged-equal-weight-continuation-v4'
const base = { observed_sharpe: 0.5, deflated_sharpe: -0.1, pbo: 0.4, parameter_stability_score: 0.2 }
const request = { n_bars: 1200, requested_folds: 3, floor: 0 }
const view = { created_at: '2026-10-23T10:00:00Z', universe_size: 20, graduated: false }

test('renders NumPy refusal plainly without fabricated score or fold evidence', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json({ ...view,
    trials: [{ ...base, strategy_name: 'xs_alpha4', purged_diagnostic: { ...request,
      method: v1, status: 'unsupported', reason: 'unsupported_numpy_version' } }],
  })))
  renderWithClient(<CrossSectionalPanel />)
  expect(await screen.findByText('not measured · unsupported NumPy version')).toBeInTheDocument()
  expect(screen.queryByText('Fold evidence')).not.toBeInTheDocument()
  expect(screen.queryByText(/same-kept-fold equal-weight universe benchmark:/i)).not.toBeInTheDocument()
  expect(screen.queryByText(/unsupported_numpy_version|restricted-shift/i)).not.toBeInTheDocument()
})

test('qualifies Alpha4 separately from existing runtime domains in a mixed production view', async () => {
  const recipes = [
    ['xs_alpha4', v4, 'rolling-alpha4-percentile-v1', 21],
    ['xs_52w_high', v2, 'rolling-high-v1', 126],
    ['xs_alpha9', v3, 'rolling-alpha9-v1', 11],
    ['xs_reversal', v1, 'shifted-reversal-v1', 4],
  ] as const
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json({ ...view,
    trials: recipes.map(([strategy_name, method, dependency_rule, lag]) => ({ ...base,
      strategy_name, purged_cv_oos_sharpe: -0.7, purged_diagnostic: { ...request,
        method, dependency_rule, max_price_lag: lag, embargo: lag, status: 'measured',
        kept_fold_ordinals: [0, 1, 2], mean_oos_sharpe: -0.7, mean_oos_hold_sharpe: -0.2 } })),
  })))
  renderWithClient(<CrossSectionalPanel />)
  await screen.findByRole('cell', { name: 'xs_alpha4' })
  const caption = screen.getByText(/Purged CV support is restricted/i)
  expect(caption).toHaveTextContent(/audited direct-shift recipes/i)
  expect(caption).toHaveTextContent(/trailing-high and Alpha9 price-change-extrema recipes restricted to pandas 3\.0\.6 Cython on complete native Float64 panels/i)
  expect(caption).toHaveTextContent(/Alpha4 window-percentile recipes restricted to pandas 3\.0\.6 Cython and NumPy 2\.5\.4 on complete native Float64 panels/i)
  for (const caveat of [/later training is intentional/i, /winning family uses the complete search sample/i,
    /account entry and switching trades are not reconciled/i, /benchmark adds no turnover-cost model/i,
    /static snapshots, not historical point-in-time/i, /equal means of retained-fold Sharpes/i,
    /not Sharpe on stitched policy returns/i]) expect(caption).toHaveTextContent(caveat)
  for (const [name] of recipes) {
    const row = screen.getByRole('cell', { name }).closest('tr')!
    expect(within(row).getByText('-0.70')).toBeInTheDocument()
    expect(within(row).getByText(/benchmark: -0.20/i)).toBeInTheDocument()
  }
  expect(screen.queryByText(/restricted-pandas|rolling-alpha|rolling-high|shifted-reversal-v1/i)).not.toBeInTheDocument()
  expect(screen.getByText('no graduate')).toBeInTheDocument()
})

test.each([null, undefined])('legacy absence %s keeps score unpaired without fold attribution', async (absent) => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json({ ...view,
    trials: [{ ...base, strategy_name: 'xs_alpha4', purged_cv_oos_sharpe: -0.7, purged_diagnostic: absent }],
  })))
  renderWithClient(<CrossSectionalPanel />)
  expect(await screen.findByText('-0.70 · legacy, unpaired')).toBeInTheDocument()
  expect(screen.queryByText('Fold evidence')).not.toBeInTheDocument()
  expect(screen.queryByText(/same-kept-fold equal-weight universe benchmark:/i)).not.toBeInTheDocument()
})
