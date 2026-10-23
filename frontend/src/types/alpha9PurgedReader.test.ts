import { crossSectionalResponseSchema } from './lab'

const v1 = 'restricted-shift-family-purged-equal-weight-continuation-v1'
const v2 = 'restricted-pandas-3.0.6-cython-high-purged-equal-weight-continuation-v2'
const v3 = 'restricted-pandas-3.0.6-cython-alpha9-purged-equal-weight-continuation-v3'
const evidence = {
  method: v3, status: 'measured', reason: null, n_bars: 1200, requested_folds: 3, floor: 0,
  dependency_rule: 'rolling-alpha9-v1', max_price_lag: 4, embargo: 4,
  kept_fold_ordinals: [0, 1, 2], mean_oos_sharpe: 0, mean_oos_hold_sharpe: -0.2,
}
const trial = { strategy_name: 'xs_alpha9', observed_sharpe: 0.5, deflated_sharpe: -0.1,
  pbo: 0.4, parameter_stability_score: 0.2, walk_forward_oos_sharpe: 0,
  purged_cv_oos_sharpe: 0, purged_diagnostic: evidence }
function view() {
  return { created_at: '2026-10-22T10:00:00Z', universe_size: 20, graduated: false,
    walk_forward_method: 'family-walk-forward-equal-weight-continuation-v1',
    walk_forward_hold_sharpe: 0, walk_forward_n_bars: 1200, walk_forward_n_splits: 3,
    trials: [structuredClone(trial), { ...structuredClone(trial), strategy_name: 'xs_52w_high',
      purged_diagnostic: { ...evidence, method: v2, dependency_rule: 'rolling-high-v1',
        max_price_lag: 126, embargo: 126 } },
    { ...structuredClone(trial), strategy_name: 'xs_reversal',
      purged_diagnostic: { ...evidence, method: v1, dependency_rule: 'shifted-reversal-v1' } }],
  }
}

test.each([4, 6, 11])('preserves Alpha9 lag %i with v1/v2/v3 in one request', (lag) => {
  const raw = view()
  Object.assign(raw.trials[0].purged_diagnostic, { max_price_lag: lag, embargo: lag })
  const parsed = crossSectionalResponseSchema.parse(raw)!
  expect(parsed.trials.map((row) => row.purged_diagnostic?.method)).toEqual([v3, v2, v1])
  expect(parsed.trials[0].purged_diagnostic).toEqual(raw.trials[0].purged_diagnostic)
})

test.each([0, -0.7])('preserves Alpha9 measured mean %s with paired benchmark', (mean) => {
  const raw = view()
  raw.trials[0].purged_cv_oos_sharpe = mean
  raw.trials[0].purged_diagnostic.mean_oos_sharpe = mean
  expect(crossSectionalResponseSchema.parse(raw)!.trials[0].purged_cv_oos_sharpe).toBe(mean)
})

test('accepts Alpha9 supported no-fold geometry without fabricated means', () => {
  const raw = view()
  raw.trials = raw.trials.slice(0, 1)
  raw.walk_forward_n_bars = 12
  Object.assign(raw.trials[0], { purged_cv_oos_sharpe: null })
  Object.assign(raw.trials[0].purged_diagnostic, { n_bars: 12, max_price_lag: 11, embargo: 11,
    status: 'no_usable_folds', kept_fold_ordinals: [], mean_oos_sharpe: null, mean_oos_hold_sharpe: null })
  expect(crossSectionalResponseSchema.parse(raw)!.trials[0].purged_diagnostic?.status).toBe('no_usable_folds')
})

test.each([
  ['v1 with Alpha9 rule', { method: v1 }],
  ['v2 with Alpha9 rule', { method: v2 }],
  ['v3 with high rule', { dependency_rule: 'rolling-high-v1' }],
  ['v3 with momentum rule', { dependency_rule: 'shifted-momentum-v1' }],
  ['v3 with reversal rule', { dependency_rule: 'shifted-reversal-v1' }],
  ['unknown method', { method: 'future-alpha9-method' }],
  ['unknown rule', { dependency_rule: 'rolling-alpha9-v2' }],
  ['wrong lag', { max_price_lag: 5, embargo: 5 }],
  ['high lag', { max_price_lag: 126, embargo: 126 }],
  ['fractional lag', { max_price_lag: 4.5, embargo: 4.5 }],
  ['boolean lag', { max_price_lag: true, embargo: true }],
  ['wrong embargo', { embargo: 3 }],
  ['wrong kept set', { kept_fold_ordinals: [0, 2] }],
  ['missing control', { mean_oos_hold_sharpe: null }],
  ['unsupported branch', { status: 'unsupported', reason: 'unsupported_factory', dependency_rule: null,
    max_price_lag: null, embargo: null, kept_fold_ordinals: null, mean_oos_sharpe: null, mean_oos_hold_sharpe: null }],
] as const)('refuses Alpha9 %s', (_label, patch) => {
  const raw = view()
  Object.assign(raw.trials[0].purged_diagnostic, patch)
  if ('status' in patch) Object.assign(raw.trials[0], { purged_cv_oos_sharpe: null })
  expect(crossSectionalResponseSchema.safeParse(raw).success).toBe(false)
})

test.each(['n_bars', 'requested_folds', 'floor'] as const)('mixed v1/v2/v3 bind common %s', (key) => {
  const raw = view()
  raw.trials[2].purged_diagnostic[key] += 1
  expect(crossSectionalResponseSchema.safeParse(raw).success).toBe(false)
})

test('mixed v1/v2/v3 bind scalar, complete evidence and WF bars', () => {
  const raw = view()
  raw.trials[0].purged_cv_oos_sharpe = 1
  expect(crossSectionalResponseSchema.safeParse(raw).success).toBe(false)
  raw.trials[0].purged_cv_oos_sharpe = 0
  raw.walk_forward_n_bars += 1
  expect(crossSectionalResponseSchema.safeParse(raw).success).toBe(false)
  raw.walk_forward_n_bars -= 1
  Object.assign(raw.trials[2], { purged_diagnostic: null })
  expect(crossSectionalResponseSchema.safeParse(raw).success).toBe(false)
})
