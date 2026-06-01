import { z } from 'zod'

// Mirrors the backend DataQualityIssue (app/data/models/quality.py).
// `context` is an arbitrary bag the engine attaches to each finding — kept open by design.
export const dataQualityIssueSchema = z.object({
  check: z.string(),
  severity: z.enum(['info', 'warning', 'error']),
  message: z.string(),
  context: z.record(z.string(), z.unknown()).nullable().optional(),
})

export type DataQualityIssue = z.infer<typeof dataQualityIssueSchema>

// Mirrors backend DataQualityReport. `passed` is server-computed (true iff no error issues).
export const dataQualityReportSchema = z.object({
  symbol: z.string(),
  checked_at: z.string(),
  issues: z.array(dataQualityIssueSchema),
  passed: z.boolean(),
})

export type DataQualityReport = z.infer<typeof dataQualityReportSchema>

// Mirrors backend IngestResponse (app/api/v1/ingest.py).
// `stored` is false when the quality gate failed; the report is persisted either way.
export const ingestResponseSchema = z.object({
  symbol: z.string(),
  bars_ingested: z.number().int().nonnegative(),
  stored: z.boolean(),
  quality_report: dataQualityReportSchema,
})

export type IngestResponse = z.infer<typeof ingestResponseSchema>

export const ingestRequestSchema = z.object({
  symbol: z.string().min(1),
  start_date: z.string(),
  end_date: z.string(),
})

export type IngestRequest = z.infer<typeof ingestRequestSchema>
