import { useState } from 'react'

import { DataExplorerPage } from './features/data-explorer/DataExplorerPage'
import { ValidationReportPage } from './features/validation-report/ValidationReportPage'

type PageId = 'validation' | 'data-explorer'

const PAGES: { id: PageId; label: string }[] = [
  { id: 'validation', label: 'Validation' },
  { id: 'data-explorer', label: 'Data Explorer' },
]

function App() {
  const [page, setPage] = useState<PageId>('validation')

  return (
    <main className="app-shell">
      <header>
        <h1>QuantForge</h1>
        <p>Quantitative research &amp; validation platform.</p>
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
    </main>
  )
}

export default App
