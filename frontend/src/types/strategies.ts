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

export const strategySchema = z.object({
  name: z.string(),
  label: z.string(),
  description: z.string(),
  citations: z.array(z.string()),
  parameters: z.array(paramSchema),
})

export type StrategySchema = z.infer<typeof strategySchema>

export const strategyCatalogSchema = z.array(strategySchema)
export type StrategyCatalog = z.infer<typeof strategyCatalogSchema>
