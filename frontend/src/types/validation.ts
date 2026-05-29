import { z } from 'zod'

// Mirrors the backend ValidationReport (api-contracts.md / app/validation/report.py).
// `passed` is server-computed and authoritative — render the verdict from it.
export const validationReportSchema = z.object({
  strategy_name: z.string(),
  observed_sharpe: z.number(),
  deflated_sharpe: z.number(),
  pbo: z.number().min(0).max(1),
  parameter_stability_score: z.number().min(0).max(1),
  n_walk_forward_splits: z.number().int(),
  n_purged_folds: z.number().int(),
  flags: z.array(z.string()),
  passed: z.boolean(),
})

export type ValidationReport = z.infer<typeof validationReportSchema>

export const STRATEGIES = ['sma', 'momentum', 'mean_reversion'] as const

export const validateRequestSchema = z.object({
  symbol: z.string().min(1),
  strategy: z.enum(STRATEGIES),
  start_date: z.string(),
  end_date: z.string(),
})

export type ValidateRequest = z.infer<typeof validateRequestSchema>
