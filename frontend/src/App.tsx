import { useValidation } from './features/validation-report/useValidation'
import { ValidationReportView } from './features/validation-report/ValidationReportView'
import type { ValidateRequest } from './types/validation'

const DEFAULT_REQUEST: ValidateRequest = {
  symbol: 'AAPL',
  strategy: 'sma',
  start_date: '2020-01-01T00:00:00Z',
  end_date: '2024-01-01T00:00:00Z',
}

function App() {
  const validation = useValidation()

  return (
    <main className="app-shell">
      <header>
        <h1>QuantForge</h1>
        <p>Quantitative research &amp; validation platform.</p>
      </header>

      <button
        type="button"
        onClick={() => validation.mutate(DEFAULT_REQUEST)}
        disabled={validation.isPending}
      >
        {validation.isPending ? 'Validating…' : 'Run validation (AAPL · SMA)'}
      </button>

      {validation.isError && <p role="alert">Validation failed — please try again.</p>}
      {validation.data && <ValidationReportView report={validation.data} />}
    </main>
  )
}

export default App
