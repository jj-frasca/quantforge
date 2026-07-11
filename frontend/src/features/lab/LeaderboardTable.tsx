import type { LeaderboardRow } from '../../types/lab'

interface Props {
  rows: LeaderboardRow[]
}

const fmtSharpe = (value: number | null | undefined): string =>
  value === null || value === undefined ? '—' : value.toFixed(2)

// Deflation verdict is a far stronger claim than a per-symbol graduate (ADR-018): does the
// holdout Sharpe clear the best-of-N-under-the-null bar? Null for non-graduates.
function deflationLabel(row: LeaderboardRow): string {
  if (!row.graduated || row.survives_universe_deflation === null || row.survives_universe_deflation === undefined) {
    return '—'
  }
  return row.survives_universe_deflation ? 'survives' : 'selection-lucky'
}

export function LeaderboardTable({ rows }: Props) {
  if (rows.length === 0) {
    return (
      <section aria-label="leaderboard" className="leaderboard empty">
        <p>No strategies in the leaderboard yet — run a hunt to populate it.</p>
      </section>
    )
  }

  const nGraduates = rows.filter((r) => r.graduated).length

  return (
    <section aria-label="leaderboard" className="leaderboard">
      <p className="summary">
        {rows.length} strateg{rows.length === 1 ? 'y' : 'ies'} tested ·{' '}
        {nGraduates} graduate{nGraduates === 1 ? '' : 's'}
      </p>
      <div className="table-scroll">
        <table className="lab-table leaderboard-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Strategy</th>
              <th>Deflated Sharpe</th>
              <th>Holdout Sharpe</th>
              <th>Graduated</th>
              <th>Universe deflation</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={`${row.symbol}-${row.strategy_name}`}
                className={row.graduated ? 'graduated' : undefined}
              >
                <td>{row.symbol}</td>
                <td>{row.strategy_name}</td>
                <td>{fmtSharpe(row.deflated_sharpe)}</td>
                <td>{fmtSharpe(row.holdout_sharpe)}</td>
                <td>
                  <span className={`status-badge ${row.graduated ? 'pass' : 'muted'}`}>
                    {row.graduated ? 'graduate' : 'rejected'}
                  </span>
                </td>
                <td>{deflationLabel(row)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
