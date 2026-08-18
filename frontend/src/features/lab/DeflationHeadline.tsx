import type { PoolReport } from '../../types/lab'

const count = (n: number) => n.toLocaleString('en-US')

// ADR-033. The headline a reader should see BEFORE any leaderboard row: of the strategies that
// cleared the graduation gate, how many are distinguishable from picking the best of N symbols by
// luck. Reporting the graduate count alone overstates the funnel, so this states both.
export function DeflationHeadline({ report }: { report: PoolReport }) {
  const { n_surviving_deflation: survivors, n_leaderboard_graduates: graduates } = report

  return (
    <div className="deflation-headline">
      <p data-testid="deflation-survivors">
        <strong>
          {count(survivors)} of {count(graduates)}
        </strong>{' '}
        graduates clear the universe-deflation bar (best-of-{count(report.n_symbols)} selection under
        the null, ADR-018).
      </p>
      <p data-testid="search-effort">
        Searched {count(report.n_experiments)} experiments over {count(report.n_symbols)} symbols —{' '}
        {count(report.n_trials)} lifetime trials, which is the denominator the deflated Sharpe and
        MinTRL penalties are charged against.
      </p>
      {survivors === 0 && (
        <p role="status" className="deflation-warning">
          Every graduate in the pool is currently <strong>not distinguishable from selection
          luck</strong>. The paper book holds {count(report.n_open_positions)} positions drawn from
          this population — they are being forward-tested, not recommended.
        </p>
      )}
      {report.near_misses.length > 0 && (
        <table>
          <caption>Closest to the bar — each against its own threshold</caption>
          <thead>
            <tr>
              <th scope="col">Symbol</th>
              <th scope="col">Strategy</th>
              <th scope="col">Holdout Sharpe</th>
              <th scope="col">Bar</th>
              <th scope="col">Holdout years</th>
            </tr>
          </thead>
          <tbody>
            {report.near_misses.map((miss) => (
              <tr key={`${miss.symbol}-${miss.strategy_name}`}>
                <td>{miss.symbol}</td>
                <td>{miss.strategy_name}</td>
                <td>{miss.holdout_sharpe.toFixed(2)}</td>
                <td>{miss.bar.toFixed(2)}</td>
                <td>{miss.holdout_years.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
