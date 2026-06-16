import { useState, type FormEvent } from 'react'

import { Field } from '../../components/ui/Field'
import { defaultDateRange } from '../../lib/defaultDateRange'
import type { ValidateRequest } from '../../types/validation'
import { groupByCategory } from '../strategies/groupByCategory'
import { useStrategies } from '../strategies/useStrategies'
import { useValidation } from './useValidation'
import { ValidationReportView } from './ValidationReportView'

// Validation runs PBO / walk-forward / purged CV — wants more data than a single
// backtest does. 5 trailing years ≈ 1260 bars, comfortable for the 10 PBO splits + 5
// walk-forward folds + 5 purged CV folds. Anchored to "today" so the defaults never
// go stale.
const { startDate: DEFAULT_START_DATE, endDate: DEFAULT_END_DATE } = defaultDateRange(5)

const DEFAULTS = {
  symbol: 'AAPL',
  strategy: 'sma',
  startDate: DEFAULT_START_DATE,
  endDate: DEFAULT_END_DATE,
}

const toIsoStartOfDay = (date: string): string => `${date}T00:00:00Z`

export function ValidationReportPage() {
  const validation = useValidation()
  const strategies = useStrategies()
  const [symbol, setSymbol] = useState(DEFAULTS.symbol)
  const [strategy, setStrategy] = useState<string>(DEFAULTS.strategy)
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

  // The catalog is the single source of truth for valid strategy names (ADR-010).
  // /validate now accepts every catalog entry — the grid is auto-generated from
  // each strategy's ParamSchema (see grid_generator.py) so we no longer maintain a
  // separate frontend whitelist that drifts. See feedback-frontend-shadow-validators.
  const catalogEntry = strategies.data?.find((s) => s.name === strategy)

  return (
    <section aria-label="validation report page" className="page validation-report">
      <header>
        <h2>Validation Report</h2>
        <p>Run the full validation suite (PBO, Deflated Sharpe, walk-forward, purged CV).</p>
      </header>

      {strategies.isError && (
        <p role="alert">Could not load the strategy catalog — refresh to retry.</p>
      )}

      {strategies.data && (
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
            <select value={strategy} onChange={(event) => setStrategy(event.target.value)}>
              {groupByCategory(strategies.data).map(({ category, entries }) => (
                <optgroup key={category} label={category}>
                  {entries.map((entry) => (
                    <option key={entry.name} value={entry.name}>
                      {entry.label}
                    </option>
                  ))}
                </optgroup>
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
      )}

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
