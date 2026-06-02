import { useState, type FormEvent } from 'react'

import { Field } from '../../components/ui/Field'
import { STRATEGIES, type ValidateRequest } from '../../types/validation'
import { useValidation } from './useValidation'
import { ValidationReportView } from './ValidationReportView'

const DEFAULTS = {
  symbol: 'AAPL',
  strategy: 'sma' as const,
  startDate: '2020-01-01',
  endDate: '2024-01-01',
}

const toIsoStartOfDay = (date: string): string => `${date}T00:00:00Z`

export function ValidationReportPage() {
  const validation = useValidation()
  const [symbol, setSymbol] = useState(DEFAULTS.symbol)
  const [strategy, setStrategy] = useState<(typeof STRATEGIES)[number]>(DEFAULTS.strategy)
  const [startDate, setStartDate] = useState(DEFAULTS.startDate)
  const [endDate, setEndDate] = useState(DEFAULTS.endDate)

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const body: ValidateRequest = {
      symbol: symbol.trim().toUpperCase(),
      strategy,
      start_date: toIsoStartOfDay(startDate),
      end_date: toIsoStartOfDay(endDate),
    }
    validation.mutate(body)
  }

  return (
    <section aria-label="validation report page" className="page validation-report">
      <header>
        <h2>Validation Report</h2>
        <p>Run the full validation suite (PBO, Deflated Sharpe, walk-forward, purged CV).</p>
      </header>

      <form onSubmit={onSubmit} className="validate-form">
        <Field label="Symbol">
          <input
            type="text"
            value={symbol}
            onChange={(event) => setSymbol(event.target.value)}
            required
          />
        </Field>
        <Field label="Strategy">
          <select
            value={strategy}
            onChange={(event) => setStrategy(event.target.value as (typeof STRATEGIES)[number])}
          >
            {STRATEGIES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Start date">
          <input
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
            required
          />
        </Field>
        <Field label="End date">
          <input
            type="date"
            value={endDate}
            onChange={(event) => setEndDate(event.target.value)}
            required
          />
        </Field>
        <button type="submit" disabled={validation.isPending}>
          {validation.isPending ? 'Validating…' : 'Run validation'}
        </button>
      </form>

      {validation.isError && (
        <p role="alert">Validation failed — {(validation.error as Error).message}</p>
      )}
      {validation.data && <ValidationReportView report={validation.data} />}
    </section>
  )
}
