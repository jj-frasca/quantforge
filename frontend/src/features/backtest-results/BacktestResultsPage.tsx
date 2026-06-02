import { useState, type FormEvent } from 'react'

import { Field } from '../../components/ui/Field'
import type { BacktestRequest, StrategyConfig } from '../../types/backtest'
import { BacktestResultView } from './BacktestResultView'
import { useBacktest } from './useBacktest'

const DEFAULT_SYMBOL = 'AAPL'
const DEFAULT_START = '2020-01-01'
const DEFAULT_END = '2024-01-01'

const DEFAULT_CONFIGS: Record<StrategyConfig['name'], StrategyConfig> = {
  sma: { name: 'sma', fast: 20, slow: 50 },
  momentum: { name: 'momentum', lookback: 60, skip: 5 },
  mean_reversion: { name: 'mean_reversion', window: 20, k: 2.0 },
}

const toIsoStartOfDay = (date: string): string => `${date}T00:00:00Z`

export function BacktestResultsPage() {
  const backtest = useBacktest()
  const [symbol, setSymbol] = useState(DEFAULT_SYMBOL)
  const [startDate, setStartDate] = useState(DEFAULT_START)
  const [endDate, setEndDate] = useState(DEFAULT_END)
  const [strategy, setStrategy] = useState<StrategyConfig>(DEFAULT_CONFIGS.sma)

  const onStrategyChange = (name: StrategyConfig['name']) => {
    setStrategy(DEFAULT_CONFIGS[name])
  }

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
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
            value={strategy.name}
            onChange={(event) => onStrategyChange(event.target.value as StrategyConfig['name'])}
          >
            <option value="sma">sma</option>
            <option value="momentum">momentum</option>
            <option value="mean_reversion">mean_reversion</option>
          </select>
        </Field>

        <StrategyParamFields config={strategy} onChange={setStrategy} />

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
        <button type="submit" disabled={backtest.isPending}>
          {backtest.isPending ? 'Running…' : 'Run backtest'}
        </button>
      </form>

      {backtest.isError && (
        <p role="alert">Backtest failed — {(backtest.error as Error).message}</p>
      )}
      {backtest.data && <BacktestResultView result={backtest.data} />}
    </section>
  )
}

interface ParamFieldsProps {
  config: StrategyConfig
  onChange: (next: StrategyConfig) => void
}

function StrategyParamFields({ config, onChange }: ParamFieldsProps) {
  if (config.name === 'sma') {
    return (
      <>
        <Field label="Fast">
          <input
            type="number"
            min={1}
            value={config.fast}
            onChange={(event) => onChange({ ...config, fast: Number(event.target.value) })}
          />
        </Field>
        <Field label="Slow">
          <input
            type="number"
            min={2}
            value={config.slow}
            onChange={(event) => onChange({ ...config, slow: Number(event.target.value) })}
          />
        </Field>
      </>
    )
  }
  if (config.name === 'momentum') {
    return (
      <>
        <Field label="Lookback">
          <input
            type="number"
            min={1}
            value={config.lookback}
            onChange={(event) =>
              onChange({ ...config, lookback: Number(event.target.value) })
            }
          />
        </Field>
        <Field label="Skip">
          <input
            type="number"
            min={0}
            value={config.skip}
            onChange={(event) => onChange({ ...config, skip: Number(event.target.value) })}
          />
        </Field>
      </>
    )
  }
  return (
    <>
      <Field label="Window">
        <input
          type="number"
          min={2}
          value={config.window}
          onChange={(event) => onChange({ ...config, window: Number(event.target.value) })}
        />
      </Field>
      <Field label="k">
        <input
          type="number"
          min={0.1}
          step={0.1}
          value={config.k}
          onChange={(event) => onChange({ ...config, k: Number(event.target.value) })}
        />
      </Field>
    </>
  )
}
