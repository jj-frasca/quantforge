import { useState, type FormEvent } from 'react'

import { Field } from '../../components/ui/Field'
import { STRATEGIES, type ValidateRequest } from '../../types/validation'
import { useStrategies } from '../strategies/useStrategies'
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
  const strategies = useStrategies()
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

  // /validate uses an internal config grid per strategy — only the strategy NAME flows
  // through the API. The catalog drives the human-readable labels in the dropdown.
  const catalogEntry = strategies.data?.find((s) => s.name === strategy)

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
            {(strategies.data ?? STRATEGIES.map((s) => ({ name: s, label: s }))).map(
              (entry) => (
                <option key={entry.name} value={entry.name}>
                  {entry.label}
                </option>
              ),
            )}
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

      {catalogEntry && (
        <section aria-label="strategy info" className="strategy-info">
          <p>{catalogEntry.description}</p>
          {catalogEntry.citations.length > 0 && (
            <ul className="citations">
              {catalogEntry.citations.map((citation) => (
                <li key={citation}>{citation}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {validation.isError && (
        <p role="alert">Validation failed — {(validation.error as Error).message}</p>
      )}
      {validation.data && <ValidationReportView report={validation.data} />}
    </section>
  )
}
