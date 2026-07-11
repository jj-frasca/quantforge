import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { PaperPosition } from '../../types/lab'

interface Props {
  positions: PaperPosition[]
}

// NOTE on "equity curve": the WP-D contract (ForwardScore) returns SCALAR forward metrics, not a
// per-bar series, so a literal equity curve can't be drawn without fabricating a time series
// (CLAUDE.md rule 6 honesty). Instead we chart the real, honest bar the ForwardScore documents:
// the strategy's forward Sharpe against simply buying and holding the same name, per position.

export function ForwardComparisonChart({ positions }: Props) {
  const scored = positions.filter((p) => p.score !== null && p.score !== undefined)
  if (scored.length === 0) {
    return (
      <section aria-label="forward vs buy-and-hold" className="forward-chart empty">
        <p>No forward scores yet — positions accrue out-of-sample bars over time.</p>
      </section>
    )
  }

  const data = scored.map((p) => ({
    symbol: p.symbol,
    strategy: p.score?.forward_sharpe ?? 0,
    benchmark: p.score?.buy_and_hold_sharpe ?? 0,
    beats: p.score?.beats_buy_and_hold ?? false,
  }))
  const nBeating = data.filter((d) => d.beats).length

  return (
    <section aria-label="forward vs buy-and-hold" className="forward-chart">
      <p className="summary">
        {nBeating} of {scored.length} position{scored.length === 1 ? '' : 's'} beating buy-and-hold
        (forward Sharpe, risk-adjusted)
      </p>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="symbol" />
          <YAxis tickFormatter={(v: number) => v.toFixed(1)} />
          <Tooltip formatter={(value) => (typeof value === 'number' ? value.toFixed(2) : String(value))} />
          <Legend />
          <ReferenceLine y={0} stroke="#94a3b8" />
          <Bar name="Strategy (forward)" dataKey="strategy">
            {data.map((d) => (
              // Green when the strategy beats buy-and-hold; amber when it doesn't — the honest signal.
              <Cell key={d.symbol} fill={d.beats ? '#22c55e' : '#f59e0b'} />
            ))}
          </Bar>
          <Bar name="Buy & hold" dataKey="benchmark" fill="#94a3b8" />
        </BarChart>
      </ResponsiveContainer>
    </section>
  )
}
