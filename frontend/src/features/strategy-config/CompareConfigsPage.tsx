import { useId, useMemo, useState, type FormEvent } from 'react'

import { Field } from '../../components/ui/Field'
import { defaultDateRange } from '../../lib/defaultDateRange'
import type { BacktestRequest } from '../../types/backtest'
import type { StrategySchema } from '../../types/strategies'
import { groupByCategory } from '../strategies/groupByCategory'
import { StrategyParamForm } from '../strategies/StrategyParamForm'
import { useStrategies } from '../strategies/useStrategies'
import { CompareEquityCurves } from './CompareEquityCurves'
import { CompareMetricsTable } from './CompareMetricsTable'
import { useCompareBacktests } from './useCompareBacktests'

// ADR-011 §Decision: cap N at 6. Floor at 2: one row is a normal backtest.
const MIN_ROWS = 2
const MAX_ROWS = 6

const { startDate: DEFAULT_START, endDate: DEFAULT_END } = defaultDateRange(5)

const defaultValuesFor = (entry: StrategySchema): Record<string, number> =>
  Object.fromEntries(entry.parameters.map((p) => [p.name, p.default]))

const allValid = (values: Record<string, number>): boolean =>
  Object.values(values).every((v) => Number.isFinite(v))

const toIsoStartOfDay = (date: string): string => `${date}T00:00:00Z`

const rowLabel = (index: number): string => `Config ${String.fromCharCode(65 + index)}`

interface Row {
  id: string
  values: Record<string, number>
}

const newId = (): string => `row-${Math.random().toString(36).slice(2, 9)}`

export function CompareConfigsPage() {
  const strategies = useStrategies()
  const catalog = strategies.data
  const formId = useId()

  const [symbol, setSymbol] = useState('AAPL')
  const [startDate, setStartDate] = useState(DEFAULT_START)
  const [endDate, setEndDate] = useState(DEFAULT_END)
  const [initialCapital, setInitialCapital] = useState(100_000)
  const [costRateBps, setCostRateBps] = useState(10)

  // The chosen strategy applies to every row — "compare configs of the SAME method"
  // is the canonical parameter-sensitivity story (ADR-011 §Context). null means
  // "fall back to the catalog's first entry until the user picks one."
  const [strategyName, setStrategyName] = useState<string | null>(null)
  const selectedEntry = useMemo(() => {
    if (!catalog) return undefined
    return strategyName ? catalog.find((s) => s.name === strategyName) : catalog[0]
  }, [catalog, strategyName])

  const [rows, setRows] = useState<Row[]>([])
  // Seed two rows the moment the catalog (and therefore the param defaults) lands, and
  // reset them whenever the user picks a different strategy. This is the "adjust state
  // while rendering when a value changes" pattern (react.dev) — keyed on the strategy
  // name so it fires once per strategy change, not on every catalog-identity churn, and
  // never on row add/remove. Doing it here instead of in an effect avoids the cascading
  // re-render that setState-in-effect causes (react-hooks/set-state-in-effect).
  const [seededFor, setSeededFor] = useState<string | null>(null)
  if (selectedEntry && seededFor !== selectedEntry.name) {
    const defaults = defaultValuesFor(selectedEntry)
    setSeededFor(selectedEntry.name)
    setRows([
      { id: newId(), values: { ...defaults } },
      { id: newId(), values: { ...defaults } },
    ])
  }

  const compare = useCompareBacktests()

  const onStrategyChange = (name: string) => {
    setStrategyName(name)
  }

  const onRowChange = (id: string, next: Record<string, number>) => {
    setRows((current) => current.map((r) => (r.id === id ? { ...r, values: next } : r)))
  }

  const onAddRow = () => {
    if (!selectedEntry || rows.length >= MAX_ROWS) return
    setRows((current) => [...current, { id: newId(), values: defaultValuesFor(selectedEntry) }])
  }

  const onRemoveRow = (id: string) => {
    setRows((current) => (current.length <= MIN_ROWS ? current : current.filter((r) => r.id !== id)))
  }

  const canSubmit =
    !!selectedEntry &&
    rows.length >= MIN_ROWS &&
    rows.every((r) => allValid(r.values)) &&
    compare.status !== 'pending'

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!selectedEntry) return
    const requests: BacktestRequest[] = rows.map((row) => ({
      symbol: symbol.trim().toUpperCase(),
      strategy: { name: selectedEntry.name, ...row.values },
      start_date: toIsoStartOfDay(startDate),
      end_date: toIsoStartOfDay(endDate),
      initial_capital: initialCapital,
      cost_rate: costRateBps / 10_000,
    }))
    void compare.submit(requests)
  }

  return (
    <section aria-label="compare configs page" className="page compare-configs">
      <header>
        <h2>Compare Configurations</h2>
        <p>
          Run 2–6 parameter sets side-by-side on the same symbol and window. The whole
          methodology behind PBO and Deflated Sharpe rests on never trusting one config in
          isolation — this page makes the spread between configs visible at a glance.
        </p>
      </header>

      {strategies.isError && (
        <p role="alert">Could not load the strategy catalog — refresh to retry.</p>
      )}

      {selectedEntry && (
        <form id={formId} onSubmit={onSubmit} className="ingest-form">
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
              value={selectedEntry.name}
              onChange={(event) => onStrategyChange(event.target.value)}
            >
              {catalog &&
                groupByCategory(catalog).map(({ category, entries }) => (
                  <optgroup key={category} label={category}>
                    {entries.map((s) => (
                      <option key={s.name} value={s.name}>
                        {s.label}
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
          <Field label="Initial capital ($)">
            <input
              type="number"
              min={1}
              step="any"
              value={initialCapital}
              onChange={(event) => setInitialCapital(Number(event.target.value))}
            />
          </Field>
          <Field label="Cost (bps)">
            <input
              type="number"
              min={0}
              step="any"
              value={costRateBps}
              onChange={(event) => setCostRateBps(Number(event.target.value))}
            />
          </Field>

          <div className="compare-rows" role="list">
            {rows.map((row, index) => (
              <fieldset
                key={row.id}
                role="group"
                aria-label={rowLabel(index)}
                className="compare-row"
              >
                <legend>{rowLabel(index)}</legend>
                <StrategyParamForm
                  parameters={selectedEntry.parameters}
                  values={row.values}
                  onChange={(next) => onRowChange(row.id, next)}
                />
                <button
                  type="button"
                  onClick={() => onRemoveRow(row.id)}
                  disabled={rows.length <= MIN_ROWS}
                >
                  Remove
                </button>
              </fieldset>
            ))}
          </div>

          <div className="compare-actions">
            <button type="button" onClick={onAddRow} disabled={rows.length >= MAX_ROWS}>
              + Add config
            </button>
            <button type="submit" disabled={!canSubmit}>
              {compare.status === 'pending' ? 'Running…' : 'Run comparison'}
            </button>
            <small className="compare-count">
              {rows.length} of {MAX_ROWS} configurations
            </small>
          </div>
        </form>
      )}

      {compare.status === 'settled' && selectedEntry && (
        <>
          <CompareEquityCurves rows={rows.map((r, i) => ({ label: rowLabel(i), values: r.values }))} results={compare.results} />
          <CompareMetricsTable
            symbol={symbol.trim().toUpperCase()}
            strategy={selectedEntry.name}
            startDate={startDate}
            endDate={endDate}
            rows={rows.map((r, i) => ({ label: rowLabel(i), values: r.values }))}
            results={compare.results}
          />
        </>
      )}
    </section>
  )
}
