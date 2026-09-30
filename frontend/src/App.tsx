import { lazy, Suspense } from 'react'

import { OnboardingBanner } from './components/ui/OnboardingBanner'
import { DataExplorerPage } from './features/data-explorer/DataExplorerPage'
import { useAppShell, type PageId } from './state/appShell'

// Data Explorer is the default page (loaded eagerly above) so first paint stays synchronous.
// The other 6 pages are code-split: each ships its own chunk (Recharts-heavy pages in
// particular) and only downloads when the user actually clicks that tab, instead of every
// visitor paying for all 7 pages' JS on first load.
const AboutPage = lazy(() =>
  import('./features/about/AboutPage').then((m) => ({ default: m.AboutPage })),
)
const BacktestResultsPage = lazy(() =>
  import('./features/backtest-results/BacktestResultsPage').then((m) => ({
    default: m.BacktestResultsPage,
  })),
)
const DiscoveriesPage = lazy(() =>
  import('./features/lab/DiscoveriesPage').then((m) => ({ default: m.DiscoveriesPage })),
)
const LabDashboardPage = lazy(() =>
  import('./features/lab/LabDashboardPage').then((m) => ({ default: m.LabDashboardPage })),
)
const CompareConfigsPage = lazy(() =>
  import('./features/strategy-config/CompareConfigsPage').then((m) => ({
    default: m.CompareConfigsPage,
  })),
)
const ValidationReportPage = lazy(() =>
  import('./features/validation-report/ValidationReportPage').then((m) => ({
    default: m.ValidationReportPage,
  })),
)

const PAGES: { id: PageId; label: string }[] = [
  { id: 'data-explorer', label: 'Data Explorer' },
  { id: 'backtest-results', label: 'Backtest Results' },
  { id: 'compare-configs', label: 'Compare Configs' },
  { id: 'validation', label: 'Validation' },
  { id: 'lab', label: 'Live' },
  { id: 'discoveries', label: 'Discoveries' },
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

      {page === 'data-explorer' && <DataExplorerPage />}
      <Suspense fallback={<p>Loading…</p>}>
        {page === 'validation' && <ValidationReportPage />}
        {page === 'backtest-results' && <BacktestResultsPage />}
        {page === 'compare-configs' && <CompareConfigsPage />}
        {page === 'lab' && <LabDashboardPage />}
        {page === 'discoveries' && <DiscoveriesPage />}
        {page === 'about' && <AboutPage />}
      </Suspense>

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
