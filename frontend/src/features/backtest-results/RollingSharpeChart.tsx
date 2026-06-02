import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { RollingSharpePoint } from '../../types/backtest'

interface Props {
  data: RollingSharpePoint[]
  window: number
}

const asRatio = (value: number): string => value.toFixed(2)

// Rolling annualized Sharpe over a fixed window. A flat-ish line above zero is the most
// trustworthy shape — a Sharpe that depends on one good year is a red flag the headline
// metric alone won't catch.
export function RollingSharpeChart({ data, window }: Props) {
  if (data.length === 0) {
    return (
      <section aria-label="rolling sharpe" className="rolling-sharpe empty">
        <p>No rolling Sharpe points returned.</p>
      </section>
    )
  }

  const chartData = data.map((point) => ({
    date: point.timestamp_utc.slice(0, 10),
    sharpe: point.sharpe,
  }))

  return (
    <section aria-label="rolling sharpe" className="rolling-sharpe">
      <p className="summary">Rolling Sharpe ({window}-bar window, annualized)</p>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" minTickGap={32} />
          <YAxis domain={['auto', 'auto']} tickFormatter={asRatio} />
          <Tooltip
            formatter={(value) =>
              typeof value === 'number' ? asRatio(value) : String(value)
            }
          />
          <ReferenceLine y={0} stroke="#94a3b8" />
          <Line type="monotone" dataKey="sharpe" stroke="#3b82f6" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </section>
  )
}
