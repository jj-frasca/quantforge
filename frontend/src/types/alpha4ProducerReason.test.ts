import { crossSectionalResponseSchema } from './lab'

const v1 = 'restricted-shift-family-purged-equal-weight-continuation-v1'
const v4 = 'restricted-pandas-3.0.6-numpy-2.5.4-cython-alpha4-purged-equal-weight-continuation-v4'
const evidence = { method: v1, status: 'unsupported', reason: 'unsupported_numpy_version',
  n_bars: 1200, requested_folds: 3, floor: 0 }
const trial = { strategy_name: 'xs_alpha4', observed_sharpe: 0.5, deflated_sharpe: -0.1,
  pbo: 0.4, parameter_stability_score: 0.2, purged_diagnostic: evidence }
const view = { created_at: '2026-10-23T10:00:00Z', universe_size: 20, graduated: false, trials: [trial] }

test('preserves NumPy refusal under unsupported v1 without invented means or support', () => {
  const parsed = crossSectionalResponseSchema.parse(view)!
  expect(parsed.trials[0].purged_diagnostic).toEqual(evidence)
  expect(parsed.trials[0].purged_cv_oos_sharpe).toBeUndefined()
})

test.each([
  { method: v4 }, { status: 'measured' }, { status: 'no_usable_folds' },
  { mean_oos_sharpe: 0 }, { mean_oos_hold_sharpe: 0 },
  { dependency_rule: 'rolling-alpha4-percentile-v1' }, { max_price_lag: 5 },
  { embargo: 5 }, { kept_fold_ordinals: [] }, { reason: 'unknown_numpy_version' },
])('refuses incompatible NumPy refusal claim %j', (patch) => {
  expect(crossSectionalResponseSchema.safeParse({ ...view, trials: [{ ...trial,
    purged_diagnostic: { ...evidence, ...patch } }] }).success).toBe(false)
})

test('NumPy refusal rejects a nonnull trial score', () => {
  expect(crossSectionalResponseSchema.safeParse({ ...view,
    trials: [{ ...trial, purged_cv_oos_sharpe: 0 }] }).success).toBe(false)
})
