// Zod schemas: parse a valid response; reject a missing field, non-numeric prices, and a
// negative bar count. Boundary validation of the /api/v1/bars contract.
import { barsResponseSchema, chartBarSchema } from './bars'

const validBar = {
  timestamp_utc: '2024-01-01T00:00:00Z',
  open: 100.5,
  high: 101.2,
  low: 99.8,
  close: 100.9,
  volume: 1_000_000,
}

test('chartBarSchema parses a valid bar', () => {
  expect(chartBarSchema.parse(validBar)).toEqual(validBar)
})

test('chartBarSchema rejects a non-numeric close', () => {
  expect(() => chartBarSchema.parse({ ...validBar, close: 'oops' })).toThrow()
})

test('barsResponseSchema parses a valid response', () => {
  const valid = { symbol: 'AAPL', n_bars: 1, bars: [validBar] }
  expect(barsResponseSchema.parse(valid)).toEqual(valid)
})

test('barsResponseSchema rejects a negative n_bars', () => {
  expect(() => barsResponseSchema.parse({ symbol: 'AAPL', n_bars: -1, bars: [] })).toThrow()
})

test('barsResponseSchema rejects a missing bars field', () => {
  expect(() => barsResponseSchema.parse({ symbol: 'AAPL', n_bars: 0 })).toThrow()
})
