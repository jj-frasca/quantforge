import {
  CartesianGrid,
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
}

const fmtMoney = (value: number): string =>
  value.toLocaleString(undefined, { maximumFractionDigits: 0 })

export function EquityCurveChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <section aria-label="equity curve" className="equity-curve empty">
        <p>No equity points returned — run a backtest above.</p>
      </section>
    )
  }

  const chartData = data.map((point) => ({
    date: point.timestamp_utc.slice(0, 10),
    equity: point.equity,
  }))
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
          <Line type="monotone" dataKey="equity" stroke="#22c55e" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </section>
  )
}
