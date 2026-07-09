import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { PaperPosition } from '../../types/lab'

interface Props {
  position: PaperPosition
}

const fmtIndex = (value: number): string => value.toFixed(3)
const fmtPct = (index: number): string => `${((index - 1) * 100).toFixed(1)}%`

// The real forward equity curve (ADR-023): a normalized index (base 1.0 at freeze) compounding
// each post-freeze bar, strategy vs buy-and-hold — on data the strategy never saw. Renders only
// once ≥2 forward bars have accrued (a single point is not a curve); the scalar comparison chart
// and the "no forward data yet" note cover the sparser cases.
export function PositionEquityCurve({ position }: Props) {
  const series = position.score?.forward_equity ?? []
  if (series.length < 2) return null

  const data = series.map((point) => ({
    date: point.timestamp.slice(0, 10),
    strategy: point.strategy_equity,
    benchmark: point.buy_and_hold_equity,
  }))
  const last = series[series.length - 1]

  return (
    <section aria-label={`equity curve ${position.symbol}`} className="position-equity-curve">
      <p className="summary">
        {position.symbol} · {position.strategy_name} · forward {fmtPct(last.strategy_equity)} vs
        buy-and-hold {fmtPct(last.buy_and_hold_equity)}
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" minTickGap={32} />
          <YAxis domain={['auto', 'auto']} tickFormatter={fmtIndex} />
          <Tooltip formatter={(value) => (typeof value === 'number' ? fmtIndex(value) : String(value))} />
          <Legend />
          <ReferenceLine y={1} stroke="#94a3b8" strokeDasharray="2 2" />
          <Line type="monotone" name="Strategy (forward)" dataKey="strategy" stroke="#22c55e" dot={false} />
          <Line
            type="monotone"
            name="Buy & hold"
            dataKey="benchmark"
            stroke="#94a3b8"
            strokeDasharray="4 4"
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </section>
  )
}
