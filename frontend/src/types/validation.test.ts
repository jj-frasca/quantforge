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

test('validateRequestSchema rejects an unknown strategy', () => {
  expect(() =>
    validateRequestSchema.parse({
      symbol: 'AAPL',
      strategy: 'bogus',
      start_date: '2020-01-01T00:00:00Z',
      end_date: '2024-01-01T00:00:00Z',
    }),
  ).toThrow()
})
