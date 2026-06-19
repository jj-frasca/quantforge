import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { CompareRow } from './useCompareBacktests'

// Distinct colors for up to 6 series (ADR-011 MAX_ROWS). Picked from the Tailwind
// palette to stay legible on both light and dark backgrounds.
const COLORS = ['#22c55e', '#3b82f6', '#f59e0b', '#a855f7', '#ef4444', '#06b6d4']

interface RowDescriptor {
  label: string
  values: Record<string, number>
}

interface Props {
  rows: RowDescriptor[]
  results: CompareRow[]
}

const fmtMoney = (value: number): string =>
  value.toLocaleString(undefined, { maximumFractionDigits: 0 })

// Renders one <Line> per successful row on a shared X-axis. Failed rows simply do
// not render a series; their failure is surfaced by the metrics table below.
//
// Implementation note: we join the successful equity curves on the date prefix
// (YYYY-MM-DD) since the backtest endpoint returns ISO-UTC strings. Misalignment
// across rows (e.g. one row's curve starting one bar later because of a longer
// warmup window) shows up as a missing point on the early bar — Recharts skips it.
export function CompareEquityCurves({ rows, results }: Props) {
  const successful = rows
    .map((row, index) => ({ row, result: results[index], index }))
    .filter(
      (entry): entry is { row: RowDescriptor; result: Extract<CompareRow, { status: 'success' }>; index: number } =>
        entry.result?.status === 'success',
    )

  if (successful.length === 0) {
    return (
      <section aria-label="comparison chart" className="compare-chart empty">
        <p>No rows returned results — see the table below for per-config errors.</p>
      </section>
    )
  }

  const datesIndex = new Map<string, Record<string, number>>()
  for (const { row, result } of successful) {
    for (const point of result.data.equity_curve) {
      const date = point.timestamp_utc.slice(0, 10)
      const bucket = datesIndex.get(date) ?? {}
      bucket[row.label] = point.equity
      datesIndex.set(date, bucket)
    }
  }
  const data = Array.from(datesIndex.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, byLabel]) => ({ date, ...byLabel }))

  return (
    <section aria-label="comparison chart" className="compare-chart">
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" minTickGap={32} />
          <YAxis domain={['auto', 'auto']} tickFormatter={fmtMoney} />
          <Tooltip
            formatter={(value) =>
              typeof value === 'number' ? `$${fmtMoney(value)}` : String(value)
            }
          />
          <Legend />
          {successful.map(({ row, index }) => (
            <Line
              key={row.label}
              type="monotone"
              name={row.label}
              dataKey={row.label}
              stroke={COLORS[index % COLORS.length]}
              dot={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </section>
  )
}
