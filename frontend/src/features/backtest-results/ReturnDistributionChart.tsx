import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { ReturnDistribution } from '../../types/backtest'

interface Props {
  data: ReturnDistribution
}

const asPercent = (value: number): string => `${(value * 100).toFixed(2)}%`
const asRatio = (value: number): string => value.toFixed(2)

// Distribution of daily returns. Skewness < 0 (left tail heavier) and excess kurtosis > 0
// (fat tails) are the danger zone — small daily wins, occasional large losses.
// Reading the shape is more honest than reading just the headline Sharpe.
export function ReturnDistributionChart({ data }: Props) {
  if (data.bins.length === 0) {
    return (
      <section aria-label="return distribution" className="return-distribution empty">
        <p>No returns to bin.</p>
      </section>
    )
  }

  const chartData = data.bins.map((bin) => ({
    bin: asPercent(bin.bin_center),
    frequency: bin.frequency,
  }))

  return (
    <section aria-label="return distribution" className="return-distribution">
      <p className="summary">
        Daily returns — skew {asRatio(data.skewness)} · excess kurtosis{' '}
        {asRatio(data.kurtosis)}
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="bin" interval="preserveStartEnd" minTickGap={32} />
          <YAxis allowDecimals={false} />
          <Tooltip
            formatter={(value) =>
              typeof value === 'number' ? `${value} bars` : String(value)
            }
          />
          <Bar dataKey="frequency" fill="#a78bfa" />
        </BarChart>
      </ResponsiveContainer>
    </section>
  )
}
