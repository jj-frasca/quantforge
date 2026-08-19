// Zod schemas: parse a valid report; reject out-of-range pbo, a missing field, and an
// unknown strategy (boundary validation of the API contract).
import { validateRequestSchema, validationReportSchema } from './validation'

const valid = {
  strategy_name: 'sma',
  observed_sharpe: 1.2,
  deflated_sharpe: 0.4,
  pbo: 0.2,
  parameter_stability_score: 0.85,
  n_walk_forward_splits: 5,
  n_purged_folds: 5,
  flags: [],
  interpretations: [],
  passed: true,
  regime_breakdown: {
    bull: { n_bars: 100, total_return: 0.1, sharpe: 1.0 },
    bear: { n_bars: 50, total_return: 0.0, sharpe: 0.5 },
  },
}

test('validationReportSchema parses a valid report', () => {
  // walk_forward (ADR-038) and purged_cv (ADR-039) default to null: a response without them
  // is "not measured", which must never be read as a measured zero.
  expect(validationReportSchema.parse(valid)).toEqual({ ...valid, walk_forward: null, purged_cv: null })
})

test('validationReportSchema rejects pbo outside [0,1]', () => {
  expect(() => validationReportSchema.parse({ ...valid, pbo: 1.5 })).toThrow()
})

test('validationReportSchema rejects a missing field', () => {
  const incomplete: Record<string, unknown> = { ...valid }
  delete incomplete.passed
  expect(() => validationReportSchema.parse(incomplete)).toThrow()
})

test('validateRequestSchema accepts any catalog strategy name', () => {
  // The frontend used to hardcode `z.enum(['sma', 'momentum', 'mean_reversion'])` and
  // silently broke when the backend extended /validate to every catalog strategy. The
  // backend catalog is the discriminator authority (ADR-010); the frontend trusts the
  // catalog-driven dropdown and lets the backend 422 anything truly invalid. See
  // [[feedback-frontend-shadow-validators]].
  expect(
    validateRequestSchema.parse({
      symbol: 'AAPL',
      strategy: 'rsi_mean_reversion',
      start_date: '2020-01-01T00:00:00Z',
      end_date: '2024-01-01T00:00:00Z',
    }),
  ).toMatchObject({ strategy: 'rsi_mean_reversion' })
})

test('validateRequestSchema rejects an empty strategy name', () => {
  // The one thing we DO enforce on the frontend: strategy must be a non-empty string.
  expect(() =>
    validateRequestSchema.parse({
      symbol: 'AAPL',
      strategy: '',
      start_date: '2020-01-01T00:00:00Z',
      end_date: '2024-01-01T00:00:00Z',
    }),
  ).toThrow()
})

// ADR-038: the walk-forward splits now carry an evaluation, not just a count.
const walkForward = {
  n_splits: 5,
  splits: [
    { selected_config: 0, is_sharpe: 1.1, oos_sharpe: 0.4, n_train: 100, n_test: 40 },
    { selected_config: 2, is_sharpe: 0.9, oos_sharpe: -0.2, n_train: 140, n_test: 40 },
  ],
  mean_is_sharpe: 1.0,
  mean_oos_sharpe: 0.1,
  consistency: 0.5,
  efficiency: 0.1,
}

test('validationReportSchema parses a walk-forward evaluation', () => {
  const parsed = validationReportSchema.parse({ ...valid, walk_forward: walkForward })
  expect(parsed.walk_forward?.mean_oos_sharpe).toBe(0.1)
  expect(parsed.walk_forward?.splits).toHaveLength(2)
})

test('validationReportSchema accepts a null efficiency (undefined under a losing in-sample)', () => {
  const parsed = validationReportSchema.parse({
    ...valid,
    walk_forward: { ...walkForward, efficiency: null },
  })
  expect(parsed.walk_forward?.efficiency).toBeNull()
})

test('validationReportSchema defaults walk_forward to null for older responses', () => {
  expect(validationReportSchema.parse(valid).walk_forward).toBeNull()
})

// ADR-039: the purged folds now carry a leakage-controlled evaluation.
const purgedCv = {
  n_folds: 5,
  embargo: 200,
  folds: [{ selected_config: 1, oos_sharpe: 0.3, n_train: 200, n_test: 60 }],
  mean_oos_sharpe: 0.25,
  oos_sharpe_std: 0.4,
  consistency: 0.6,
}

test('validationReportSchema parses a purged-CV evaluation', () => {
  const parsed = validationReportSchema.parse({ ...valid, purged_cv: purgedCv })
  expect(parsed.purged_cv?.embargo).toBe(200)
  expect(parsed.purged_cv?.oos_sharpe_std).toBe(0.4)
})

test('validationReportSchema defaults purged_cv to null when nothing was purged', () => {
  expect(validationReportSchema.parse(valid).purged_cv).toBeNull()
})
