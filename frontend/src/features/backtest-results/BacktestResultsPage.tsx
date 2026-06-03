import { useState, type FormEvent } from 'react'

import { Field } from '../../components/ui/Field'
import {
  backtestRequestSchema,
  type BacktestRequest,
  type StrategyConfig,
} from '../../types/backtest'
import type { StrategySchema } from '../../types/strategies'
import { StrategyParamForm } from '../strategies/StrategyParamForm'
import { useStrategies } from '../strategies/useStrategies'
import { BacktestResultView } from './BacktestResultView'
import { useBacktest } from './useBacktest'

const DEFAULT_SYMBOL = 'AAPL'
const DEFAULT_START = '2020-01-01'
const DEFAULT_END = '2024-01-01'

const toIsoStartOfDay = (date: string): string => `${date}T00:00:00Z`

const defaultValuesFor = (entry: StrategySchema): Record<string, number> =>
  Object.fromEntries(entry.parameters.map((p) => [p.name, p.default]))

const allParamsValid = (values: Record<string, number>): boolean =>
  Object.values(values).every((v) => Number.isFinite(v))

// Derived form state: selection + param values are kept in a single `overrides` slot,
// null means "show catalog defaults for the first strategy". This sidesteps the React 19
// rule against setState-in-useEffect for catalog-initialization.
interface StrategySelection {
  name: string
  values: Record<string, number>
}

export function BacktestResultsPage() {
  const backtest = useBacktest()
  const strategies = useStrategies()
  const [symbol, setSymbol] = useState(DEFAULT_SYMBOL)
  const [startDate, setStartDate] = useState(DEFAULT_START)
  const [endDate, setEndDate] = useState(DEFAULT_END)
  const [selection, setSelection] = useState<StrategySelection | null>(null)

  const catalog = strategies.data
  const selectedEntry = selection
    ? catalog?.find((s) => s.name === selection.name)
    : catalog?.[0]
  const selectedName = selectedEntry?.name ?? ''
  const paramValues =
    selection?.values ?? (selectedEntry ? defaultValuesFor(selectedEntry) : {})

  const onStrategyChange = (name: string) => {
    const entry = catalog?.find((s) => s.name === name)
    if (entry) setSelection({ name, values: defaultValuesFor(entry) })
  }

  const onParamChange = (next: Record<string, number>) => {
    if (!selectedEntry) return
    setSelection({ name: selectedEntry.name, values: next })
  }

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!selectedName) return
    // Build via the discriminated union schema — invalid combinations throw at the
    // boundary rather than reaching the server.
    const strategy = backtestRequestSchema.shape.strategy.parse({
      name: selectedName,
      ...paramValues,
    }) as StrategyConfig
    const body: BacktestRequest = {
      symbol: symbol.trim().toUpperCase(),
      strategy,
      start_date: toIsoStartOfDay(startDate),
      end_date: toIsoStartOfDay(endDate),
    }
    backtest.mutate(body)
  }

  return (
    <section aria-label="backtest results page" className="page backtest-results">
      <header>
        <h2>Backtest Results</h2>
        <p>Run a single backtest of one config — no overfitting suite.</p>
      </header>

      {strategies.isError && (
        <p role="alert">Could not load the strategy catalog — refresh to retry.</p>
      )}

      {strategies.data && selectedEntry && (
        <form onSubmit={onSubmit} className="ingest-form">
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
              value={selectedName}
              onChange={(event) => onStrategyChange(event.target.value)}
            >
              {strategies.data.map((s) => (
                <option key={s.name} value={s.name}>
                  {s.label}
                </option>
              ))}
            </select>
          </Field>

          <StrategyParamForm
            parameters={selectedEntry.parameters}
            values={paramValues}
            onChange={onParamChange}
          />

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
          <button type="submit" disabled={backtest.isPending || !allParamsValid(paramValues)}>
            {backtest.isPending ? 'Running…' : 'Run backtest'}
          </button>
        </form>
      )}

      {selectedEntry && (
        <section aria-label="strategy info" className="strategy-info">
          <p>{selectedEntry.description}</p>
          {selectedEntry.citations.length > 0 && (
            <ul className="citations">
              {selectedEntry.citations.map((citation) => (
                <li key={citation}>{citation}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {backtest.isError && (
        <p role="alert">Backtest failed — {(backtest.error as Error).message}</p>
      )}
      {backtest.data && <BacktestResultView result={backtest.data} />}
    </section>
  )
}
