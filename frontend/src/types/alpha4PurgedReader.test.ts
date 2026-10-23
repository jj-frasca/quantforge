import { crossSectionalResponseSchema } from './lab'

const v1 = 'restricted-shift-family-purged-equal-weight-continuation-v1'
const v2 = 'restricted-pandas-3.0.6-cython-high-purged-equal-weight-continuation-v2'
const v3 = 'restricted-pandas-3.0.6-cython-alpha9-purged-equal-weight-continuation-v3'
const v4 = 'restricted-pandas-3.0.6-numpy-2.5.4-cython-alpha4-purged-equal-weight-continuation-v4'
const evidence = {
  method: v4, status: 'measured', reason: null, n_bars: 1200, requested_folds: 3, floor: 0,
  dependency_rule: 'rolling-alpha4-percentile-v1', max_price_lag: 5, embargo: 5,
  kept_fold_ordinals: [0, 1, 2], mean_oos_sharpe: 0, mean_oos_hold_sharpe: -0.2,
}
const trial = { strategy_name: 'xs_alpha4', observed_sharpe: 0.5, deflated_sharpe: -0.1,
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
      purged_diagnostic: { ...evidence, method: v1, dependency_rule: 'shifted-reversal-v1', max_price_lag: 4, embargo: 4 } },
    { ...structuredClone(trial), strategy_name: 'xs_alpha9',
      purged_diagnostic: { ...evidence, method: v3, dependency_rule: 'rolling-alpha9-v1',
        max_price_lag: 11, embargo: 11 } }],
  }
}

test.each([5, 9, 21])('preserves Alpha4 lag %i with v1/v2/v3/v4 in one request', (lag) => {
  const raw = view()
  Object.assign(raw.trials[0].purged_diagnostic, { max_price_lag: lag, embargo: lag })
  const parsed = crossSectionalResponseSchema.parse(raw)!
  expect(parsed.trials.map((row) => row.purged_diagnostic?.method)).toEqual([v4, v2, v1, v3])
  expect(parsed.trials[0].purged_diagnostic).toEqual(raw.trials[0].purged_diagnostic)
})

test.each([0, -0.7])('preserves Alpha4 measured mean %s with paired benchmark', (mean) => {
  const raw = view()
  raw.trials[0].purged_cv_oos_sharpe = mean
  raw.trials[0].purged_diagnostic.mean_oos_sharpe = mean
  expect(crossSectionalResponseSchema.parse(raw)!.trials[0].purged_cv_oos_sharpe).toBe(mean)
})

test('accepts Alpha4 supported no-fold geometry without fabricated means', () => {
  const raw = view()
  raw.trials = raw.trials.slice(0, 1)
  raw.walk_forward_n_bars = 12
  Object.assign(raw.trials[0], { purged_cv_oos_sharpe: null })
  Object.assign(raw.trials[0].purged_diagnostic, { n_bars: 12, max_price_lag: 21, embargo: 21,
    status: 'no_usable_folds', kept_fold_ordinals: [], mean_oos_sharpe: null, mean_oos_hold_sharpe: null })
  expect(crossSectionalResponseSchema.parse(raw)!.trials[0].purged_diagnostic?.status).toBe('no_usable_folds')
})

test.each([
  ['v1 with Alpha4 rule', { method: v1 }],
  ['v2 with Alpha4 rule', { method: v2 }],
  ['v3 with Alpha4 rule', { method: v3 }],
  ['v4 with Alpha9 rule', { dependency_rule: 'rolling-alpha9-v1' }],
  ['v4 with high rule', { dependency_rule: 'rolling-high-v1' }],
  ['v4 with momentum rule', { dependency_rule: 'shifted-momentum-v1' }],
  ['v4 with reversal rule', { dependency_rule: 'shifted-reversal-v1' }],
  ['unknown method', { method: 'future-alpha4-method' }],
  ['unknown rule', { dependency_rule: 'rolling-alpha4-v2' }],
  ['wrong lag', { max_price_lag: 6, embargo: 6 }],
  ['high lag', { max_price_lag: 126, embargo: 126 }],
  ['fractional lag', { max_price_lag: 4.5, embargo: 4.5 }],
  ['boolean lag', { max_price_lag: true, embargo: true }],
  ['wrong embargo', { embargo: 3 }],
  ['wrong kept set', { kept_fold_ordinals: [0, 2] }],
  ['missing control', { mean_oos_hold_sharpe: null }],
  ['nonfinite mean', { mean_oos_sharpe: Infinity }],
  ['nonfinite control', { mean_oos_hold_sharpe: NaN }],
  ['unknown status', { status: 'pending' }],
  ['no-fold with retained geometry', { status: 'no_usable_folds', mean_oos_sharpe: null, mean_oos_hold_sharpe: null }],
  ['unsupported branch', { status: 'unsupported', reason: 'unsupported_factory', dependency_rule: null,
    max_price_lag: null, embargo: null, kept_fold_ordinals: null, mean_oos_sharpe: null, mean_oos_hold_sharpe: null }],
] as const)('refuses Alpha4 %s', (_label, patch) => {
  const raw = view()
  Object.assign(raw.trials[0].purged_diagnostic, patch)
  if ('status' in patch) Object.assign(raw.trials[0], { purged_cv_oos_sharpe: null })
  expect(crossSectionalResponseSchema.safeParse(raw).success).toBe(false)
})

test.each([null, undefined])('preserves historical Alpha4 unpaired scalar with evidence %s', (absent) => {
  const raw = view()
  raw.trials = raw.trials.slice(0, 1)
  Object.assign(raw.trials[0], { purged_diagnostic: absent, purged_cv_oos_sharpe: -0.7 })
  const parsed = crossSectionalResponseSchema.parse(raw)!
  expect(parsed.trials[0].purged_cv_oos_sharpe).toBe(-0.7)
  expect(parsed.trials[0].purged_diagnostic).toBe(absent)
})

test.each(['n_bars', 'requested_folds', 'floor'] as const)('mixed v1/v2/v3/v4 bind common %s', (key) => {
  const raw = view()
  raw.trials[2].purged_diagnostic[key] += 1
  expect(crossSectionalResponseSchema.safeParse(raw).success).toBe(false)
})

test('mixed v1/v2/v3/v4 bind scalar, complete evidence and WF bars', () => {
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
