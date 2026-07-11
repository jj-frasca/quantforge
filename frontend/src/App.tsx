import { OnboardingBanner } from './components/ui/OnboardingBanner'
import { AboutPage } from './features/about/AboutPage'
import { BacktestResultsPage } from './features/backtest-results/BacktestResultsPage'
import { DataExplorerPage } from './features/data-explorer/DataExplorerPage'
import { LabDashboardPage } from './features/lab/LabDashboardPage'
import { CompareConfigsPage } from './features/strategy-config/CompareConfigsPage'
import { ValidationReportPage } from './features/validation-report/ValidationReportPage'
import { useAppShell, type PageId } from './state/appShell'

const PAGES: { id: PageId; label: string }[] = [
  { id: 'data-explorer', label: 'Data Explorer' },
  { id: 'backtest-results', label: 'Backtest Results' },
  { id: 'compare-configs', label: 'Compare Configs' },
  { id: 'validation', label: 'Validation' },
  { id: 'lab', label: 'Live' },
  { id: 'about', label: 'About' },
]

function App() {
  const page = useAppShell((state) => state.activePage)
  const setPage = useAppShell((state) => state.setActivePage)

  return (
    <main className="app-shell">
      <header>
        <div className="brand-row">
          <h1>QuantForge</h1>
          <a
            className="repo-link"
            href="https://github.com/jj-frasca/quantforge"
            target="_blank"
            rel="noreferrer"
          >
            GitHub ↗
          </a>
        </div>
        <p>
          AI-native quantitative research platform. Ingest market data, run honest backtests,
          and validate strategies with PBO, Deflated Sharpe, walk-forward, and purged CV.
        </p>
        <OnboardingBanner />
        <nav aria-label="primary" className="primary-nav">
          {PAGES.map((p) => (
            <button
              key={p.id}
              type="button"
              aria-current={page === p.id ? 'page' : undefined}
              onClick={() => setPage(p.id)}
            >
              {p.label}
            </button>
          ))}
        </nav>
      </header>

      {page === 'validation' && <ValidationReportPage />}
      {page === 'data-explorer' && <DataExplorerPage />}
      {page === 'backtest-results' && <BacktestResultsPage />}
      {page === 'compare-configs' && <CompareConfigsPage />}
      {page === 'lab' && <LabDashboardPage />}
      {page === 'about' && <AboutPage />}

      <footer className="app-footer">
        <small>
          Built with React 19 + TypeScript + FastAPI + TimescaleDB. Methodology:{' '}
          López de Prado &amp; Bailey (2014–2017).
        </small>
      </footer>
    </main>
  )
}

export default App
