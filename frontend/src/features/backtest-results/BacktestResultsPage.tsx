import { useState, type FormEvent } from 'react'

import { Field } from '../../components/ui/Field'
import { defaultDateRange } from '../../lib/defaultDateRange'
import { useAppShell } from '../../state/appShell'
import type { BacktestRequest, StrategyConfig } from '../../types/backtest'
import type { StrategySchema } from '../../types/strategies'
import { groupByCategory } from '../strategies/groupByCategory'
import { PresetCards } from '../strategies/PresetCards'
import type { Preset } from '../strategies/presets'
import { StrategyParamForm } from '../strategies/StrategyParamForm'
import { useStrategies } from '../strategies/useStrategies'
import { BacktestResultView } from './BacktestResultView'
import { useBacktest } from './useBacktest'

const DEFAULT_SYMBOL = 'AAPL'
// Trailing 5-year window: ~1260 trading bars, comfortable margin past every catalog
// strategy's longest warmup (trend_window=100, slow=100). Anchored to "today" so the
// defaults never go stale as the project sits on master.
const { startDate: DEFAULT_START, endDate: DEFAULT_END } = defaultDateRange(5)
const DEFAULT_INITIAL_CAPITAL = 100_000
const DEFAULT_COST_RATE_BPS = 10  // 10 bps == 0.001 fraction. We use bps on the form so
// the user types "10" instead of "0.001" — the unit conversion (bps -> fraction) is
// applied in onSubmit so the wire payload stays in the canonical 0.001 form.

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
  const [initialCapital, setInitialCapital] = useState<number>(DEFAULT_INITIAL_CAPITAL)
  const [costRateBps, setCostRateBps] = useState<number>(DEFAULT_COST_RATE_BPS)
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

  const onLoadPreset = (preset: Preset) => {
    setSymbol(preset.symbol)
    setSelection({ name: preset.strategy.name, values: { ...preset.strategy.params } })
    const range = defaultDateRange(preset.yearsBack)
    setStartDate(range.startDate)
    setEndDate(range.endDate)
    // Capital + cost stay at the form defaults — the preset's story is the
    // (symbol, strategy, params, window), not the engine knobs.
  }

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!selectedName) return
    // The catalog-driven form already constrains `name` to known options and `paramValues`
    // to numeric inputs; the backend StrategyConfig discriminated union is the authority
    // on shape (ADR-010). Send the body as-is and rely on the 422 path if anything
    // doesn't match — no second source of truth here.
    const strategy: StrategyConfig = { name: selectedName, ...paramValues }
    const body: BacktestRequest = {
      symbol: symbol.trim().toUpperCase(),
      strategy,
      start_date: toIsoStartOfDay(startDate),
      end_date: toIsoStartOfDay(endDate),
      initial_capital: initialCapital,
      // bps (typed by the user) -> fraction (the backend's wire format).
      cost_rate: costRateBps / 10_000,
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
        <>
          <p className="quick-run-nudge">
            👉 Every field below is pre-filled with sensible defaults. Click{' '}
            <strong>Run backtest</strong> to try it — tweak anything if you want.
          </p>
          <PresetCards onLoad={onLoadPreset} />
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
              {groupByCategory(strategies.data).map(({ category, entries }) => (
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
          <Field
            label="Initial capital ($)"
            hint="Starting equity for the backtest; defaults to $100,000."
          >
            <input
              type="number"
              min={1}
              step="any"
              value={initialCapital}
              onChange={(event) => setInitialCapital(Number(event.target.value))}
            />
          </Field>
          <Field
            label="Cost (bps)"
            hint="Transaction cost per unit turnover, in basis points (10 bps = 0.10%)."
          >
            <input
              type="number"
              min={0}
              step="any"
              value={costRateBps}
              onChange={(event) => setCostRateBps(Number(event.target.value))}
            />
          </Field>
          <button type="submit" disabled={backtest.isPending || !allParamsValid(paramValues)}>
            {backtest.isPending ? 'Running…' : 'Run backtest'}
          </button>
          </form>
        </>
      )}

      {selectedEntry && (
        <section aria-label="strategy info" className="strategy-info">
          <p className="strategy-summary">{selectedEntry.summary}</p>
          <p className="strategy-description">{selectedEntry.description}</p>
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
      {backtest.data && selectedEntry && (
        <>
          <BacktestResultView result={backtest.data} />
          <div className="post-result-bridge">
            <p>
              In-sample numbers look good?{' '}
              Run the full validation suite to see whether they survive PBO and the
              Deflated Sharpe penalty.
            </p>
            <button
              type="button"
              className="validate-strategy-bridge"
              onClick={() =>
                useAppShell.getState().requestValidation({
                  symbol: symbol.trim().toUpperCase(),
                  strategy: selectedEntry.name,
                  startDate,
                  endDate,
                })
              }
            >
              Validate this strategy →
            </button>
          </div>
        </>
      )}
    </section>
  )
}
