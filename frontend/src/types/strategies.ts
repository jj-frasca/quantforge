import { z } from 'zod'

// Mirrors backend ParamSchema (app/research/strategies/catalog.py).
// `type` drives the input control and how we coerce the value on submit.
export const paramSchema = z.object({
  name: z.string(),
  type: z.enum(['int', 'float']),
  default: z.number(),
  minimum: z.number().nullable().optional(),
  maximum: z.number().nullable().optional(),
  step: z.number().nullable().optional(),
  label: z.string(),
  description: z.string().nullable().optional(),
})

export type ParamSchema = z.infer<typeof paramSchema>

// Mirror of backend StrategyCategory Literal. Used to group dropdown options into
// <optgroup>s; if the backend adds a new category, this Zod enum must be extended in the
// same commit (a missing variant means the new strategy fails the boundary parse).
export const STRATEGY_CATEGORIES = ['Trend', 'Mean Reversion', 'Breakout', 'Combination'] as const

export const strategySchema = z.object({
  name: z.string(),
  label: z.string(),
  category: z.enum(STRATEGY_CATEGORIES),
  // One plain-English sentence — distinct from `description` (which carries the
  // implementation nuance). This is the strategy's user-facing face on the
  // strategy-info panel.
  summary: z.string(),
  description: z.string(),
  citations: z.array(z.string()),
  parameters: z.array(paramSchema),
})

export type StrategySchema = z.infer<typeof strategySchema>
export type StrategyCategory = (typeof STRATEGY_CATEGORIES)[number]

export const strategyCatalogSchema = z.array(strategySchema)
export type StrategyCatalog = z.infer<typeof strategyCatalogSchema>
