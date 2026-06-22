import { z } from 'zod'

export const interpretationSchema = z.object({
  metric: z.string(),
  message: z.string(),
  verdict: z.enum(['good', 'warning', 'bad']),
})

export type Interpretation = z.infer<typeof interpretationSchema>

// One bucket of the regime breakdown — strategy performance restricted to bull
// OR bear bars. ADR-012; the backend computes this for the BEST config only.
export const regimeBreakdownEntrySchema = z.object({
  n_bars: z.number().int().nonnegative(),
  total_return: z.number(),
  sharpe: z.number(),
})

export type RegimeBreakdownEntry = z.infer<typeof regimeBreakdownEntrySchema>

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
  interpretations: z.array(interpretationSchema),
  passed: z.boolean(),
  // Keys are open-set ("bull" / "bear" today; possibly "sideways" in the future
  // per ADR-012 §Consequences). Default {} so test fixtures and older responses
  // still parse.
  regime_breakdown: z.record(z.string(), regimeBreakdownEntrySchema).default({}),
})

export type ValidationReport = z.infer<typeof validationReportSchema>

// Strategy contract is owned by the BACKEND catalog (ADR-010). The frontend used to
// pin this to the original three names; that broke the moment /validate started
// supporting every catalog strategy via auto-generated grids. See
// [[feedback-frontend-shadow-validators]] — never re-validate at the frontend a
// constraint the backend owns.
export const validateRequestSchema = z.object({
  symbol: z.string().min(1),
  strategy: z.string().min(1),
  start_date: z.string(),
  end_date: z.string(),
})

export type ValidateRequest = z.infer<typeof validateRequestSchema>
