import { crossSectionalResponseSchema } from './lab'

const highMethod = 'restricted-pandas-3.0.6-cython-high-purged-equal-weight-continuation-v2'
const shiftMethod = 'restricted-shift-family-purged-equal-weight-continuation-v1'
const high = {
  method: highMethod, status: 'measured', n_bars: 1200, requested_folds: 3, floor: 0,
  reason: null, dependency_rule: 'rolling-high-v1', max_price_lag: 126, embargo: 126,
  kept_fold_ordinals: [0, 1, 2], mean_oos_sharpe: 0, mean_oos_hold_sharpe: -0.2,
}
const trial = {
  strategy_name: 'xs_52w_high', observed_sharpe: 0.5, deflated_sharpe: -0.1,
  pbo: 0.4, parameter_stability_score: 0.2, purged_cv_oos_sharpe: 0,
  purged_diagnostic: high, walk_forward_oos_sharpe: 0,
}
function view() {
  return {
    created_at: '2026-10-22T10:00:00Z', universe_size: 20, graduated: false,
    walk_forward_method: 'family-walk-forward-equal-weight-continuation-v1',
    walk_forward_hold_sharpe: 0, walk_forward_n_bars: 1200, walk_forward_n_splits: 3,
    trials: [structuredClone(trial), { ...structuredClone(trial), strategy_name: 'xs_reversal',
      purged_cv_oos_sharpe: -0.3, purged_diagnostic: { ...high, method: shiftMethod,
        dependency_rule: 'shifted-reversal-v1', max_price_lag: 4, embargo: 4, mean_oos_sharpe: -0.3 } },
    { ...structuredClone(trial), strategy_name: 'xs_unsupported', purged_cv_oos_sharpe: null,
      purged_diagnostic: { ...high, method: shiftMethod, status: 'unsupported',
        reason: 'unsupported_factory', dependency_rule: null, max_price_lag: null,
        embargo: null, kept_fold_ordinals: null, mean_oos_sharpe: null, mean_oos_hold_sharpe: null } }],
  }
}

test.each([126, 189, 252])('retains high method at lag %i alongside shift and unsupported families', (lag) => {
  const raw = view()
  Object.assign(raw.trials[0].purged_diagnostic, { max_price_lag: lag, embargo: lag })
  const parsed = crossSectionalResponseSchema.parse(raw)!
  expect(parsed.trials.map((row) => row.purged_diagnostic?.method)).toEqual([highMethod, shiftMethod, shiftMethod])
  expect(parsed.trials[0].purged_diagnostic?.dependency_rule).toBe('rolling-high-v1')
  expect(parsed.trials[0].purged_cv_oos_sharpe).toBe(0)
  expect(parsed.trials[1].purged_cv_oos_sharpe).toBe(-0.3)
})

test('accepts supported high no-fold evidence with absent paired means', () => {
  const raw = view()
  raw.walk_forward_n_bars = 300
  for (const row of raw.trials) row.purged_diagnostic.n_bars = 300
  Object.assign(raw.trials[0], { purged_cv_oos_sharpe: null })
  Object.assign(raw.trials[0].purged_diagnostic, { status: 'no_usable_folds',
    max_price_lag: 252, embargo: 252, kept_fold_ordinals: [],
    mean_oos_sharpe: null, mean_oos_hold_sharpe: null })
  expect(crossSectionalResponseSchema.safeParse(raw).success).toBe(true)
})

test('preserves negative high measured means', () => {
  const raw = view()
  raw.trials[0].purged_cv_oos_sharpe = -0.7
  raw.trials[0].purged_diagnostic.mean_oos_sharpe = -0.7
  expect(crossSectionalResponseSchema.parse(raw)!.trials[0].purged_cv_oos_sharpe).toBe(-0.7)
})

test.each([
  ['old method with high rule', { method: shiftMethod }],
  ['high method with shift rule', { dependency_rule: 'shifted-reversal-v1' }],
  ['high method with momentum rule', { dependency_rule: 'shifted-momentum-v1' }],
  ['high method with unsupported status', { status: 'unsupported', reason: 'unsupported_factory',
    dependency_rule: null, max_price_lag: null, embargo: null, kept_fold_ordinals: null,
    mean_oos_sharpe: null, mean_oos_hold_sharpe: null }],
  ['unknown method', { method: 'future-high-method' }],
  ['unknown rule', { dependency_rule: 'rolling-high-v2' }],
  ['unaudited lag', { max_price_lag: 127, embargo: 127 }],
  ['fractional lag', { max_price_lag: 126.5, embargo: 126.5 }],
  ['boolean lag', { max_price_lag: true, embargo: true }],
  ['wrong embargo', { embargo: 125 }],
  ['wrong kept folds', { kept_fold_ordinals: [0, 2] }],
  ['missing paired mean', { mean_oos_hold_sharpe: null }],
] as const)('refuses %s', (_label, patch) => {
  const raw = view()
  Object.assign(raw.trials[0].purged_diagnostic, patch)
  if ('status' in patch && patch.status === 'unsupported') Object.assign(raw.trials[0], { purged_cv_oos_sharpe: null })
  expect(crossSectionalResponseSchema.safeParse(raw).success).toBe(false)
})

test.each(['n_bars', 'requested_folds', 'floor'] as const)('mixed methods retain common %s binding', (key) => {
  const raw = view()
  raw.trials[2].purged_diagnostic[key] += 1
  expect(crossSectionalResponseSchema.safeParse(raw).success).toBe(false)
})

test('mixed methods require every family evidence', () => {
  const raw = view()
  Object.assign(raw.trials[1], { purged_diagnostic: null })
  expect(crossSectionalResponseSchema.safeParse(raw).success).toBe(false)
})

test('mixed methods retain scalar binding and attributed WF-bar agreement', () => {
  const raw = view()
  raw.trials[0].purged_cv_oos_sharpe = 1
  expect(crossSectionalResponseSchema.safeParse(raw).success).toBe(false)
  raw.trials[0].purged_cv_oos_sharpe = 0
  raw.walk_forward_n_bars += 1
  expect(crossSectionalResponseSchema.safeParse(raw).success).toBe(false)
})

test.each(['unsupported_pandas_version', 'unsupported_rolling_engine'] as const)(
  'preserves v1 %s refusal in a mixed-method request and rejects v2 refusal', (reason) => {
    const raw = view()
    raw.trials[2].purged_diagnostic.reason = reason
    const parsed = crossSectionalResponseSchema.parse(raw)!
    expect(parsed.trials[2].purged_diagnostic?.reason).toBe(reason)
    expect(parsed.trials[2].purged_diagnostic?.method).toBe(shiftMethod)
    expect(parsed.trials[2].purged_cv_oos_sharpe).toBeNull()
    expect(parsed.trials[0].purged_diagnostic?.method).toBe(highMethod)
    raw.trials[2].purged_diagnostic.method = highMethod
    expect(crossSectionalResponseSchema.safeParse(raw).success).toBe(false)
  },
)
