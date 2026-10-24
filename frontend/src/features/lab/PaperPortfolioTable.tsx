import type { PaperPosition } from '../../types/lab'

interface Props {
  positions: PaperPosition[]
}

const fmtSharpe = (value: number | undefined): string =>
  value === undefined ? '—' : value.toFixed(2)

const fmtPct = (value: number | undefined): string =>
  value === undefined ? '—' : `${(value * 100).toFixed(1)}%`

export function PaperPortfolioTable({ positions }: Props) {
  if (positions.length === 0) {
    return (
      <section aria-label="paper portfolio" className="paper-portfolio empty">
        <p>No paper positions yet — graduates are frozen here for forward testing.</p>
      </section>
    )
  }

  const nOpen = positions.filter((p) => p.status === 'open').length

  return (
    <section aria-label="paper portfolio" className="paper-portfolio">
      <p className="summary">
        {positions.length} position{positions.length === 1 ? '' : 's'} · {nOpen} open
      </p>
      <p className="section-lede">
        Forward trade counts record turnover events. Legacy default-zero counts do not attest historical execution.
      </p>
      <div className="table-scroll">
        <table className="lab-table paper-portfolio-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Strategy</th>
              <th>Status</th>
              <th>Forward Sharpe</th>
              <th>Buy &amp; hold</th>
              <th>Forward return</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => {
              const score = position.score ?? undefined
              const beats = score?.beats_buy_and_hold ?? false
              // ADR-362: preserve affirmative served evidence without inferring original returns.
              const hasReturnEvidence = score !== undefined && (
                score.forward_sharpe !== 0 || score.forward_return !== 0 ||
                score.forward_equity.some((point) => point.strategy_equity !== 1)
              )
              const unmeasured = score !== undefined && score.forward_bars > 0 &&
                score.forward_trades === 0 && !hasReturnEvidence
              return (
                <tr
                  key={`${position.symbol}-${position.strategy_name}`}
                  className={position.status === 'closed' ? 'closed' : 'open'}
                >
                  <td>{position.symbol}</td>
                  <td>{position.strategy_name}</td>
                  <td>
                    <span className={`status-badge ${position.status === 'open' ? 'pass' : 'muted'}`}>
                      {position.status}
                    </span>
                  </td>
                  <td className={score && !unmeasured ? (beats ? 'beats' : 'lags') : undefined}>
                    {unmeasured ? '—' : fmtSharpe(score?.forward_sharpe)}
                  </td>
                  <td>{fmtSharpe(score?.buy_and_hold_sharpe)}</td>
                  <td>{unmeasured ? '—' : fmtPct(score?.forward_return)}</td>
                  <td>
                    {position.status === 'closed' && position.exit_reasons.length > 0 ? (
                      <ul className="exit-reasons">
                        {position.exit_reasons.map((reason) => (
                          <li key={reason}>{reason}</li>
                        ))}
                      </ul>
                    ) : unmeasured ? (
                      `no nonzero forward evidence recorded — 0 forward turnover events in ${score.forward_bars} forward bar${score.forward_bars === 1 ? '' : 's'}`
                    ) : score ? (
                      `${score.forward_trades === 0 ? '0 forward turnover events in ' : ''}${score.forward_bars} forward bar${score.forward_bars === 1 ? '' : 's'}`
                    ) : (
                      'no forward data yet'
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
