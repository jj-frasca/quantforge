import { z } from 'zod'

// Mirrors the backend ChartBar (app/api/v1/bars.py).
// Prices come over the wire as JSON numbers because /bars projects PriceBar -> float at the
// boundary; the chart doesn't need Decimal precision.
export const chartBarSchema = z.object({
  timestamp_utc: z.string(),
  open: z.number(),
  high: z.number(),
  low: z.number(),
  close: z.number(),
  volume: z.number().int().nonnegative(),
})

export type ChartBar = z.infer<typeof chartBarSchema>

export const barsResponseSchema = z.object({
  symbol: z.string(),
  n_bars: z.number().int().nonnegative(),
  bars: z.array(chartBarSchema),
})

export type BarsResponse = z.infer<typeof barsResponseSchema>

export interface BarsQuery {
  symbol: string
  start_date: string
  end_date: string
}
