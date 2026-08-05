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

import type { EquityPoint } from '../../types/lab'
import { useEquityCurve } from './useEquityCurve'

const PAPER_START = 100_000

const fmtCurrency = (value: number): string =>
  `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

const fmtCompact = (value: number): string =>
  `$${value.toLocaleString('en-US', { notation: 'compact', maximumFractionDigits: 1 })}`

// Signed cumulative return vs the $100k paper start — the honest "are we making money?" number.
const fmtReturn = (value: number): string => `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`

export function EquityCurvePanel() {
  const curve = useEquityCurve()

  return (
    <section aria-label="equity curve section" className="lab-section">
      <h3>Paper account — are we making money?</h3>
      <p className="section-lede">
        The real Alpaca paper account, snapshotted on every broker run. Return is measured against the
        $100,000 paper starting equity, and accrues as forward time passes — no cherry-picking.
      </p>
      {curve.isPending && <p role="status">Loading equity curve…</p>}
      {curve.isError && (
        <p role="alert">Could not load the equity curve — {(curve.error as Error).message}</p>
      )}
      {curve.data && <EquityCurveView points={curve.data} />}
    </section>
  )
}

function EquityCurveView({ points }: { points: EquityPoint[] }) {
  if (points.length === 0) {
    return (
      <div className="equity-curve empty">
        <p>No equity snapshots yet — the curve fills in as the paper broker runs.</p>
      </div>
    )
  }

  const latest = points[points.length - 1]
  const asOf = latest.timestamp.slice(0, 10)
  const up = latest.return_since_start >= 0

  const data = points.map((p) => ({ date: p.timestamp.slice(0, 10), equity: p.equity }))

  return (
    <div className="equity-curve">
      <div className="equity-headline">
        <span className="equity-value">{fmtCurrency(latest.equity)}</span>
        <span className={`status-badge ${up ? 'pass' : 'muted'}`}>
          {fmtReturn(latest.return_since_start)} since $100k start
        </span>
      </div>
      <p className="summary">
        as of {asOf} · cash {fmtCurrency(latest.cash)} · {latest.n_positions} position
        {latest.n_positions === 1 ? '' : 's'}
      </p>
      {data.length >= 2 ? (
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" minTickGap={32} />
            <YAxis domain={['auto', 'auto']} tickFormatter={fmtCompact} width={72} />
            <Tooltip
              formatter={(value) => (typeof value === 'number' ? fmtCurrency(value) : String(value))}
            />
            <ReferenceLine y={PAPER_START} stroke="#94a3b8" strokeDasharray="4 4" label="start" />
            <Line type="monotone" name="Equity" dataKey="equity" stroke="#22c55e" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <p className="note">The curve renders once a second snapshot accrues.</p>
      )}
    </div>
  )
}
