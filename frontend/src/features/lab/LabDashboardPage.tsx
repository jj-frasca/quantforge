import { DeflationHeadline } from './DeflationHeadline'
import { ForwardComparisonChart } from './ForwardComparisonChart'
import { LeaderboardTable } from './LeaderboardTable'
import { PaperPortfolioTable } from './PaperPortfolioTable'
import { PositionEquityCurve } from './PositionEquityCurve'
import { useLeaderboard } from './useLeaderboard'
import { usePaperPortfolio } from './usePaperPortfolio'
import { usePoolReport } from './usePoolReport'

export function LabDashboardPage() {
  const leaderboard = useLeaderboard()
  const portfolio = usePaperPortfolio()
  const report = usePoolReport()

  return (
    <section aria-label="live dashboard page" className="page lab-dashboard">
      <header>
        <h2>Live</h2>
        <p>
          The autonomous lab: strategies mass-tested across the universe, winners frozen and
          paper-traded forward with a managed lifecycle that exits decaying edges.
        </p>
      </header>

      {/* ADR-033: the selection-luck verdict leads, before any leaderboard row. It is a summary,
          not a precondition — if it fails to load the rest of the dashboard still renders. */}
      <section aria-label="honest headline" className="lab-section">
        {report.data && <DeflationHeadline report={report.data} />}
      </section>

      <section aria-label="paper book" className="lab-section">
        <h3>Paper portfolio</h3>
        {portfolio.isPending && <p role="status">Loading paper portfolio…</p>}
        {portfolio.isError && (
          <p role="alert">Could not load the paper portfolio — {(portfolio.error as Error).message}</p>
        )}
        {portfolio.data && (
          <>
            <PaperPortfolioTable positions={portfolio.data} />
            <ForwardComparisonChart positions={portfolio.data} />
            <div className="equity-curves">
              {portfolio.data.map((position) => (
                <PositionEquityCurve
                  key={`${position.symbol}-${position.strategy_name}`}
                  position={position}
                />
              ))}
            </div>
          </>
        )}
      </section>

      <section aria-label="leaderboard section" className="lab-section">
        <h3>Cross-symbol leaderboard</h3>
        {leaderboard.isPending && <p role="status">Loading leaderboard…</p>}
        {leaderboard.isError && (
          <p role="alert">Could not load the leaderboard — {(leaderboard.error as Error).message}</p>
        )}
        {leaderboard.data && <LeaderboardTable rows={leaderboard.data} />}
      </section>
    </section>
  )
}
