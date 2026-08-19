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

// One walk-forward window: the config picked on the train block, and how it then did on the
// block that followed. ADR-038.
export const walkForwardSplitSchema = z.object({
  selected_config: z.number().int().nonnegative(),
  is_sharpe: z.number(),
  oos_sharpe: z.number(),
  n_train: z.number().int().nonnegative(),
  n_test: z.number().int().nonnegative(),
})

// `efficiency` is null when the mean in-sample Sharpe was not positive — the backend refuses to
// report a ratio of two negative Sharpes, which would read as "efficient" while both halves lost
// money. Render the null as "n/a", never as 0.
export const walkForwardSchema = z.object({
  n_splits: z.number().int().nonnegative(),
  splits: z.array(walkForwardSplitSchema),
  mean_is_sharpe: z.number(),
  mean_oos_sharpe: z.number(),
  consistency: z.number().min(0).max(1),
  efficiency: z.number().nullable().default(null),
})

export type WalkForward = z.infer<typeof walkForwardSchema>

// One purged fold: the config chosen on the purged training rows, scored on the fold. ADR-039.
export const purgedCvFoldSchema = z.object({
  selected_config: z.number().int().nonnegative(),
  oos_sharpe: z.number(),
  n_train: z.number().int().nonnegative(),
  n_test: z.number().int().nonnegative(),
})

// Read this NEXT TO walk_forward, never instead of it: a purged fold's training rows include
// indices AFTER its test block, so it measures how stable the edge is across regimes with
// boundary leakage removed — not what the procedure would have earned. ADR-039.
export const purgedCvSchema = z.object({
  n_folds: z.number().int().nonnegative(),
  embargo: z.number().int().nonnegative(),
  folds: z.array(purgedCvFoldSchema),
  mean_oos_sharpe: z.number(),
  oos_sharpe_std: z.number().nonnegative(),
  consistency: z.number().min(0).max(1),
})

export type PurgedCv = z.infer<typeof purgedCvSchema>

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
  // Null on any report produced before ADR-038, and on producers that have no per-config
  // return matrix to walk forward. Null means NOT MEASURED — never treat it as zero.
  walk_forward: walkForwardSchema.nullable().default(null),
  // Null when the sample was too short to hold the folds plus an honest embargo — the backend
  // refuses to shrink the embargo to fit, which would yield a leaky number labelled "purged".
  purged_cv: purgedCvSchema.nullable().default(null),
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
