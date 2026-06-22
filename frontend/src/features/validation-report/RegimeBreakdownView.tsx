import type { RegimeBreakdownEntry } from '../../types/validation'

interface Props {
  breakdown: Record<string, RegimeBreakdownEntry>
}

// Sharpe gap above which the "only works in X" framing earns its place — picked
// qualitatively: 0.6 Sharpe between regimes is wide enough that the strategy's
// edge is regime-dependent in a meaningful way, and naming that gap is the
// methodology hook this component exists for (ADR-012).
const FRAGILITY_GAP = 0.6

const fmtNum = (value: number, digits = 2): string => value.toFixed(digits)
const fmtPct = (value: number): string => `${(value * 100).toFixed(1)}%`

const fragileLabel = (
  entries: { label: string; sharpe: number }[],
): string | null => {
  if (entries.length < 2) return null
  const sorted = [...entries].sort((a, b) => b.sharpe - a.sharpe)
  const [best, worst] = sorted
  if (best.sharpe - worst.sharpe < FRAGILITY_GAP) return null
  return best.label
}

export function RegimeBreakdownView({ breakdown }: Props) {
  const entries = Object.entries(breakdown).map(([label, value]) => ({
    label,
    ...value,
  }))
  if (entries.length === 0) return null

  const fragile = fragileLabel(entries)

  return (
    <section
      role="region"
      aria-label="regime breakdown"
      className="regime-breakdown"
    >
      <h3>Regime breakdown</h3>
      <table>
        <thead>
          <tr>
            <th>Regime</th>
            <th>Bars</th>
            <th>Sharpe</th>
            <th>Total return</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.label}>
              <td className="regime-label">{e.label}</td>
              <td>{e.n_bars}</td>
              <td>{fmtNum(e.sharpe)}</td>
              <td>{fmtPct(e.total_return)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {fragile && (
        <p className="regime-fragility-flag">
          Strategy only works in <strong>{fragile}</strong> regimes — a market
          regime change could erase the edge entirely.
        </p>
      )}
    </section>
  )
}
