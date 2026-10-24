import { screen, waitForElementToBeRemoved, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'

import { server } from '../../test/server'
import { renderWithClient } from '../../test/utils'
import { CrossSectionalPanel } from './CrossSectionalPanel'

const view = {
  created_at: '2026-07-26T10:00:00Z',
  universe_size: 51,
  best_strategy_name: 'xs_momentum',
  graduated: false,
  graduate_holdout_sharpe: null,
  trials: [
    {
      strategy_name: 'xs_momentum',
      observed_sharpe: 0.5,
      deflated_sharpe: -0.08,
      pbo: 0.44,
      parameter_stability_score: 0.22,
      ic_mean: 0.021,
      ic_t_stat: 3.42,
    },
    {
      strategy_name: 'xs_reversal',
      observed_sharpe: -1.2,
      deflated_sharpe: -1.68,
      pbo: 0.0,
      parameter_stability_score: 0.79,
    },
  ],
}

test('renders the latest hunt: universe size, best strategy and per-strategy trials', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json(view)))
  renderWithClient(<CrossSectionalPanel />)

  expect(await screen.findByRole('cell', { name: 'xs_momentum' })).toBeInTheDocument()
  expect(screen.getByText(/51 names/)).toBeInTheDocument()
  expect(screen.getByText(/best: xs_momentum/)).toBeInTheDocument()
  expect(screen.getByText('no graduate')).toBeInTheDocument()
  // PBO + parameter stability render as percentages.
  expect(screen.getByRole('cell', { name: '44%' })).toBeInTheDocument()
})

test('renders the empty state when no cross-sectional hunt has run (null)', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json(null)))
  renderWithClient(<CrossSectionalPanel />)

  expect(await screen.findByText(/no cross-sectional hunt has run yet/i)).toBeInTheDocument()
})

test('shows a graduate verdict + holdout Sharpe when a strategy graduated', async () => {
  server.use(
    http.get('/api/v1/cross-sectional', () =>
      HttpResponse.json({ ...view, graduated: true, graduate_holdout_sharpe: 0.63 }),
    ),
  )
  renderWithClient(<CrossSectionalPanel />)

  expect(await screen.findByText('graduate')).toBeInTheDocument()
  expect(screen.getByText(/holdout Sharpe 0.63/)).toBeInTheDocument()
})

test('reads "no ranked strategy" when best_strategy_name is null', async () => {
  server.use(
    http.get('/api/v1/cross-sectional', () =>
      HttpResponse.json({ ...view, best_strategy_name: null }),
    ),
  )
  renderWithClient(<CrossSectionalPanel />)

  expect(await screen.findByText(/no ranked strategy/)).toBeInTheDocument()
})

test('shows an error message when the cross-sectional endpoint fails', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => new HttpResponse(null, { status: 500 })))
  renderWithClient(<CrossSectionalPanel />)

  expect(await screen.findByText(/could not load the cross-sectional hunt/i)).toBeInTheDocument()
})

test('shows a loading indicator while the hunt is pending', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json(view)))
  renderWithClient(<CrossSectionalPanel />)

  await waitForElementToBeRemoved(() => screen.queryByText(/loading cross-sectional hunt/i))
  expect(await screen.findByRole('cell', { name: 'xs_momentum' })).toBeInTheDocument()
})

test('shows the rank IC per trial, and "not measured" for a pre-ADR-035 trial', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json(view)))
  renderWithClient(<CrossSectionalPanel />)

  // Mean IC is tiny by nature (a 0.02 IC is a real factor), so it needs 3 decimals.
  expect(await screen.findByRole('cell', { name: '0.021' })).toBeInTheDocument()
  expect(screen.getByRole('cell', { name: '3.4' })).toBeInTheDocument()
  // xs_reversal carries no IC: it must read as absent, never as 0.
  expect(screen.getAllByRole('cell', { name: '—' })).toHaveLength(2)
})

test.each([
  /signal\/next-return rank association/i,
  /current searches compute it on the search sample for the family finalist selected by in-sample Sharpe/i,
  /IC t-stat assumes independent periods, with no serial-dependence or search-selection adjustment/i,
  /screening diagnostic, not independent validation or a graduation gate/i,
])('keeps the IC interpretation qualification visible: %s', async (qualification) => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json(view)))
  renderWithClient(<CrossSectionalPanel />)
  await screen.findByRole('cell', { name: 'xs_momentum' })

  expect(screen.getByText(qualification)).toBeInTheDocument()
})

test('labels the IC t-stat independent-period assumption beside unchanged evidence', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json(view)))
  renderWithClient(<CrossSectionalPanel />)
  await screen.findByRole('cell', { name: 'xs_momentum' })

  expect(screen.getByRole('columnheader', { name: 'IC t-stat (independent periods)' })).toBeInTheDocument()
  expect(screen.getAllByRole('columnheader')).toHaveLength(9)
  expect(screen.getByRole('cell', { name: '0.021' })).toBeInTheDocument()
  expect(screen.getByRole('cell', { name: '3.4' })).toBeInTheDocument()
  expect(screen.getAllByRole('cell', { name: '—' })).toHaveLength(2)
  expect(screen.getByText('no graduate')).toBeInTheDocument()
})


const measuredView = {
  ...view,
  walk_forward_method: 'family-walk-forward-equal-weight-continuation-v1',
  walk_forward_hold_sharpe: -0.12,
  walk_forward_n_bars: 60,
  walk_forward_n_splits: 3,
  trials: view.trials.map((trial, index) => ({
    ...trial, walk_forward_oos_sharpe: index === 0 ? 0 : -0.37,
  })),
}

test('shows attributed family window means with the paired benchmark and actual geometry', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json(measuredView)))
  renderWithClient(<CrossSectionalPanel />)
  const momentum = (await screen.findByRole('cell', { name: 'xs_momentum' })).closest('tr')!
  const reversal = screen.getByRole('cell', { name: 'xs_reversal' }).closest('tr')!
  expect(screen.getByRole('columnheader', { name: 'Walk-forward mean Sharpe' })).toBeInTheDocument()
  expect(within(momentum).getByRole('cell', { name: '0.00' })).toBeInTheDocument()
  expect(within(reversal).getByRole('cell', { name: '-0.37' })).toBeInTheDocument()
  expect(screen.getByText(/equal mean of same-window equal-weight universe benchmark Sharpes: -0.12/i)).toBeInTheDocument()
  expect(screen.getByText(/60 search bars · 3 windows/i)).toBeInTheDocument()
  expect(screen.queryByText(/family-walk-forward-equal-weight-continuation-v1/)).not.toBeInTheDocument()
})

test('shows missing family scores as not measured without inventing pairing or geometry', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json({
    ...view, trials: view.trials.map((trial, index) => ({
      ...trial, ...(index === 0 ? { walk_forward_oos_sharpe: null } : {}),
    })),
  })))
  renderWithClient(<CrossSectionalPanel />)
  await screen.findByRole('cell', { name: 'xs_momentum' })
  // Keep the original WF assertion scoped to its column as PCV adds its own missing cells.
  for (const row of screen.getAllByRole('row').slice(1)) {
    expect(within(row).getAllByRole('cell')[5]).toHaveTextContent(/^not measured$/)
  }
  expect(screen.queryByText(/same-window equal-weight universe benchmark Sharpes/i)).not.toBeInTheDocument()
  expect(screen.queryByText(/search bars ·/i)).not.toBeInTheDocument()
})

test('labels method-null scalar as legacy, unpaired without a paired benchmark caption', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json({
    ...view, walk_forward_method: null,
    trials: view.trials.map((trial) => ({ ...trial, walk_forward_oos_sharpe: -0.42 })),
  })))
  renderWithClient(<CrossSectionalPanel />)
  await screen.findByRole('cell', { name: 'xs_momentum' })
  expect(screen.getAllByRole('cell', { name: '-0.42 · legacy, unpaired' })).toHaveLength(2)
  expect(screen.queryByText(/same-window equal-weight universe benchmark Sharpes/i)).not.toBeInTheDocument()
  expect(screen.queryByText(/search bars ·/i)).not.toBeInTheDocument()
})

test('keeps family selection, account costs, static snapshots and purged CV limits visible', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json(measuredView)))
  renderWithClient(<CrossSectionalPanel />)
  await screen.findByRole('cell', { name: 'xs_momentum' })
  expect(screen.getByText(/within each family uses earlier training rows/i)).toBeInTheDocument()
  expect(screen.getByText(/winning family uses the complete search sample/i)).toBeInTheDocument()
  expect(screen.getByText(/continued configurations include internal costs/i)).toBeInTheDocument()
  expect(screen.getByText(/account entry and switching trades are not reconciled/i)).toBeInTheDocument()
  expect(screen.getByText(/benchmark adds no turnover-cost model/i)).toBeInTheDocument()
  expect(screen.getByText(/static snapshots, not historical point-in-time/i)).toBeInTheDocument()
  expect(screen.getByText(/equal means of window Sharpes, not Sharpe on stitched policy returns/i)).toBeInTheDocument()
  expect(screen.getByText(/later training is intentional/i)).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: 'Purged CV mean Sharpe' })).toBeInTheDocument()
  expect(screen.getAllByRole('columnheader')).toHaveLength(9)
})

test('malformed attributed metadata reaches the existing error state', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json({
    ...measuredView, walk_forward_hold_sharpe: null,
  })))
  renderWithClient(<CrossSectionalPanel />)
  expect(await screen.findByRole('alert')).toHaveTextContent(/could not load the cross-sectional hunt/i)
  expect(screen.queryByRole('cell', { name: 'xs_momentum' })).not.toBeInTheDocument()
})

const panelPcvEvidence = {
  method: 'restricted-shift-family-purged-equal-weight-continuation-v1', status: 'measured',
  n_bars: 60, requested_folds: 3, floor: 0, reason: null, dependency_rule: 'shifted-reversal-v1',
  max_price_lag: 4, embargo: 4, kept_fold_ordinals: [0, 1, 2],
  mean_oos_sharpe: 0, mean_oos_hold_sharpe: -0.12,
}
const panelPcvView = { ...view, trials: view.trials.map((trial, index) => ({
  ...trial, purged_cv_oos_sharpe: index === 0 ? 0 : -0.37,
  purged_diagnostic: index === 0 ? panelPcvEvidence : { ...panelPcvEvidence,
    max_price_lag: 30, embargo: 30, kept_fold_ordinals: [0, 2],
    mean_oos_sharpe: -0.37, mean_oos_hold_sharpe: 0.7 },
})) }

test('PCV shows family-specific means, paired controls and collapsed fold evidence', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json(panelPcvView)))
  renderWithClient(<CrossSectionalPanel />)
  const first = (await screen.findByRole('cell', { name: 'xs_momentum' })).closest('tr')!
  const second = screen.getByRole('cell', { name: 'xs_reversal' }).closest('tr')!
  expect(within(first).getByText('0.00')).toBeInTheDocument()
  expect(within(second).getByText('-0.37')).toBeInTheDocument()
  expect(within(first).getByText(/same-kept-fold equal-weight universe benchmark: -0.12/i)).toBeInTheDocument()
  expect(within(second).getByText(/same-kept-fold equal-weight universe benchmark: 0.70/i)).toBeInTheDocument()
  const disclosures = screen.getAllByText('Fold evidence')
  expect(disclosures).toHaveLength(2)
  expect(disclosures[0].closest('details')).not.toHaveAttribute('open')
  expect(within(second).getByText(/60 search bars/i)).toBeInTheDocument()
  expect(within(second).getByText(/2 of 3 folds kept/i)).toBeInTheDocument()
  expect(within(second).getByText(/original floor: 0/i)).toBeInTheDocument()
  expect(within(second).getByText(/allocated price lag: 30/i)).toBeInTheDocument()
  expect(within(second).getByText(/embargo: 30/i)).toBeInTheDocument()
  expect(within(second).getByText(/kept fold numbers: 1, 3/i)).toBeInTheDocument()
  expect(screen.queryByText(/restricted-shift-family-purged|shifted-reversal-v1/i)).not.toBeInTheDocument()
  expect(screen.getByText('no graduate')).toBeInTheDocument()
  expect(screen.getByText(/audited direct-shift recipes/i)).toBeInTheDocument()
})

test.each([
  ['unsupported_factory', /unsupported or custom recipe/i],
  ['unsupported_parameters', /unsupported parameters/i],
  ['unsupported_price_dtype', /unsupported price format/i],
] as const)('PCV gives unsupported %s a plain-language explanation', async (reason, label) => {
  const evidence = { ...panelPcvEvidence, status: 'unsupported', reason,
    dependency_rule: null, max_price_lag: null, embargo: null, kept_fold_ordinals: null,
    mean_oos_sharpe: null, mean_oos_hold_sharpe: null }
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json({ ...view,
    trials: view.trials.map((trial) => ({ ...trial, purged_cv_oos_sharpe: null, purged_diagnostic: evidence })),
  })))
  renderWithClient(<CrossSectionalPanel />)
  await screen.findByRole('cell', { name: 'xs_momentum' })
  expect(screen.getAllByText(label)).toHaveLength(2)
  expect(screen.queryByText('Fold evidence')).not.toBeInTheDocument()
})

test('PCV distinguishes supported no-usable-fold geometry from unsupported recipes', async () => {
  const evidence = { ...panelPcvEvidence, status: 'no_usable_folds', max_price_lag: 60,
    embargo: 60, kept_fold_ordinals: [], mean_oos_sharpe: null, mean_oos_hold_sharpe: null }
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json({ ...view,
    trials: view.trials.map((trial) => ({ ...trial, purged_cv_oos_sharpe: null, purged_diagnostic: evidence })),
  })))
  renderWithClient(<CrossSectionalPanel />)
  await screen.findByRole('cell', { name: 'xs_momentum' })
  expect(screen.getAllByText(/not measured · no usable folds/i)).toHaveLength(2)
  expect(screen.getAllByText(/0 of 3 folds kept/i)).toHaveLength(2)
  expect(screen.getAllByText('Fold evidence')).toHaveLength(2)
  expect(screen.queryByText(/same-kept-fold equal-weight universe benchmark:/i)).not.toBeInTheDocument()
})

test('PCV historical scalar is unpaired while historical null is not measured', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json({ ...view,
    trials: view.trials.map((trial, index) => ({ ...trial,
      purged_cv_oos_sharpe: index === 0 ? -0.42 : null, purged_diagnostic: null })),
  })))
  renderWithClient(<CrossSectionalPanel />)
  const first = (await screen.findByRole('cell', { name: 'xs_momentum' })).closest('tr')!
  const second = screen.getByRole('cell', { name: 'xs_reversal' }).closest('tr')!
  expect(within(first).getByText('-0.42 · legacy, unpaired')).toBeInTheDocument()
  expect(within(second).getAllByRole('cell', { name: 'not measured' })).toHaveLength(2)
  expect(screen.queryByText('Fold evidence')).not.toBeInTheDocument()
  expect(screen.queryByText(/same-kept-fold equal-weight universe benchmark:/i)).not.toBeInTheDocument()
})

test('PCV malformed evidence reaches the error state without rendering a rounded or invented score', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json({ ...panelPcvView,
    trials: panelPcvView.trials.map((trial) => ({ ...trial, purged_cv_oos_sharpe: 5 })),
  })))
  renderWithClient(<CrossSectionalPanel />)
  expect(await screen.findByRole('alert')).toHaveTextContent(/could not load the cross-sectional hunt/i)
  expect(screen.queryByRole('cell', { name: 'xs_momentum' })).not.toBeInTheDocument()
})
