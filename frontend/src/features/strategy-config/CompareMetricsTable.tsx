import type { CompareRow } from './useCompareBacktests'

interface RowDescriptor {
  label: string
  values: Record<string, number>
}

interface Props {
  rows: RowDescriptor[]
  results: CompareRow[]
}

const fmtNum = (value: number, digits = 2): string => value.toFixed(digits)
const fmtPct = (value: number): string => `${(value * 100).toFixed(1)}%`

// Renders one table row per (config row, result row) pair. A failed row spans the
// numeric columns with its error so the user sees WHY that config didn't render —
// the per-row error promise from ADR-011 §Decision is load-bearing here.
export function CompareMetricsTable({ rows, results }: Props) {
  return (
    <table aria-label="comparison" className="compare-metrics-table">
      <thead>
        <tr>
          <th>Config</th>
          <th>Params</th>
          <th>Sharpe</th>
          <th>Annualized return</th>
          <th>Max drawdown</th>
          <th>Total return</th>
          <th>Trades</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => {
          const result = results[index]
          const paramSummary = Object.entries(row.values)
            .map(([key, value]) => `${key}=${value}`)
            .join(', ')
          if (!result || result.status === 'error') {
            return (
              <tr key={row.label}>
                <td>{row.label}</td>
                <td>{paramSummary}</td>
                <td colSpan={5} className="compare-row-error">
                  {result?.error?.message ?? 'No result returned.'}
                </td>
              </tr>
            )
          }
          const m = result.data.metrics
          return (
            <tr key={row.label}>
              <td>{row.label}</td>
              <td>{paramSummary}</td>
              <td>{fmtNum(m.sharpe)}</td>
              <td>{fmtPct(m.annualized_return)}</td>
              <td>{fmtPct(m.max_drawdown)}</td>
              <td>{fmtPct(m.total_return)}</td>
              <td>{result.data.n_trades}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
