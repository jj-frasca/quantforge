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
}

test('validationReportSchema parses a valid report', () => {
  expect(validationReportSchema.parse(valid)).toEqual(valid)
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
