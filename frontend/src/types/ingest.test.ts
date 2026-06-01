// Zod schemas: parse a valid ingest response; reject invalid severity, missing field,
// negative bars_ingested. Boundary validation of the /api/v1/ingest contract.
import { dataQualityReportSchema, ingestRequestSchema, ingestResponseSchema } from './ingest'

const validReport = {
  symbol: 'AAPL',
  checked_at: '2024-01-02T00:00:00Z',
  issues: [
    {
      check: 'missing_bars',
      severity: 'warning' as const,
      message: 'flags potential gap of 3 bars',
      context: { gap: 3 },
    },
  ],
  passed: true,
}

const validResponse = {
  symbol: 'AAPL',
  bars_ingested: 30,
  stored: true,
  quality_report: validReport,
}

test('ingestResponseSchema parses a valid response', () => {
  expect(ingestResponseSchema.parse(validResponse)).toEqual(validResponse)
})

test('dataQualityReportSchema accepts an empty issues list', () => {
  expect(dataQualityReportSchema.parse({ ...validReport, issues: [] })).toMatchObject({
    issues: [],
    passed: true,
  })
})

test('dataQualityReportSchema rejects an unknown severity', () => {
  const bad = { ...validReport, issues: [{ ...validReport.issues[0], severity: 'urgent' }] }
  expect(() => dataQualityReportSchema.parse(bad)).toThrow()
})

test('ingestResponseSchema rejects a negative bars_ingested', () => {
  expect(() => ingestResponseSchema.parse({ ...validResponse, bars_ingested: -1 })).toThrow()
})

test('ingestResponseSchema rejects a missing field', () => {
  const incomplete: Record<string, unknown> = { ...validResponse }
  delete incomplete.stored
  expect(() => ingestResponseSchema.parse(incomplete)).toThrow()
})

test('ingestRequestSchema rejects an empty symbol', () => {
  expect(() =>
    ingestRequestSchema.parse({
      symbol: '',
      start_date: '2024-01-01T00:00:00Z',
      end_date: '2024-12-01T00:00:00Z',
    }),
  ).toThrow()
})
