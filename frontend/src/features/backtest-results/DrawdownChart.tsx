import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { DrawdownPoint } from '../../types/backtest'

interface Props {
  data: DrawdownPoint[]
}

const asPercent = (value: number): string => `${(value * 100).toFixed(1)}%`

// Underwater plot: equity/cummax - 1, always ≤ 0, with 0 being "at peak". A wider, deeper
// underwater region means a more painful drawdown. This is the most honest visualization
// of strategy pain — far more informative than just "max drawdown = -18%".
export function DrawdownChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <section aria-label="drawdown" className="drawdown empty">
        <p>No drawdown points returned.</p>
      </section>
    )
  }

  const chartData = data.map((point) => ({
    date: point.timestamp_utc.slice(0, 10),
    drawdown: point.drawdown,
  }))
  const worst = Math.min(...data.map((p) => p.drawdown))

  return (
    <section aria-label="drawdown" className="drawdown">
      <p className="summary">Max drawdown {asPercent(worst)}</p>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" minTickGap={32} />
          <YAxis tickFormatter={(value: number) => asPercent(value)} domain={[-1, 0]} />
          <Tooltip
            formatter={(value) =>
              typeof value === 'number' ? asPercent(value) : String(value)
            }
          />
          <ReferenceLine y={0} stroke="#94a3b8" />
          <Area
            type="monotone"
            dataKey="drawdown"
            stroke="#ef4444"
            fill="#ef4444"
            fillOpacity={0.25}
          />
        </AreaChart>
      </ResponsiveContainer>
    </section>
  )
}
