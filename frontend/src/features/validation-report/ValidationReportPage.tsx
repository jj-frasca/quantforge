import type { ValidateRequest } from '../../types/validation'
import { useValidation } from './useValidation'
import { ValidationReportView } from './ValidationReportView'

const DEFAULT_REQUEST: ValidateRequest = {
  symbol: 'AAPL',
  strategy: 'sma',
  start_date: '2020-01-01T00:00:00Z',
  end_date: '2024-01-01T00:00:00Z',
}

export function ValidationReportPage() {
  const validation = useValidation()

  return (
    <section aria-label="validation report page" className="page validation-report">
      <header>
        <h2>Validation Report</h2>
        <p>Run the full validation suite (PBO, Deflated Sharpe, walk-forward).</p>
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
    </section>
  )
}
