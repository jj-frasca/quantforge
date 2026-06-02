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

import type { EquityPoint } from '../../types/backtest'

interface Props {
  data: EquityPoint[]
  benchmark?: EquityPoint[]
  benchmarkLabel?: string
}

const fmtMoney = (value: number): string =>
  value.toLocaleString(undefined, { maximumFractionDigits: 0 })

export function EquityCurveChart({ data, benchmark, benchmarkLabel = 'Buy & hold' }: Props) {
  if (data.length === 0) {
    return (
      <section aria-label="equity curve" className="equity-curve empty">
        <p>No equity points returned — run a backtest above.</p>
      </section>
    )
  }

  // Index the benchmark by date string for a fast join — assumes both curves share
  // the same timestamps (true for buy-and-hold of the SAME symbol).
  const benchByDate = new Map(
    (benchmark ?? []).map((point) => [point.timestamp_utc.slice(0, 10), point.equity]),
  )
  const chartData = data.map((point) => {
    const date = point.timestamp_utc.slice(0, 10)
    return {
      date,
      strategy: point.equity,
      benchmark: benchByDate.get(date),
    }
  })
  const last = data[data.length - 1].equity
  const first = data[0].equity
  const change = last / first - 1

  return (
    <section aria-label="equity curve" className="equity-curve">
      <p className="summary">
        Ending equity ${fmtMoney(last)} ({(change * 100).toFixed(1)}%)
      </p>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" minTickGap={32} />
          <YAxis domain={['auto', 'auto']} tickFormatter={fmtMoney} />
          <Tooltip
            formatter={(value) =>
              typeof value === 'number' ? `$${fmtMoney(value)}` : String(value)
            }
          />
          <Legend />
          <Line
            type="monotone"
            name="Strategy"
            dataKey="strategy"
            stroke="#22c55e"
            dot={false}
          />
          {benchmark && benchmark.length > 0 && (
            <Line
              type="monotone"
              name={benchmarkLabel}
              dataKey="benchmark"
              stroke="#94a3b8"
              strokeDasharray="4 4"
              dot={false}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </section>
  )
}
