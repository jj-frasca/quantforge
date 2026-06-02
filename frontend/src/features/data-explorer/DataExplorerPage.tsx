import { useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import type { BarsQuery } from '../../types/bars'
import type { IngestRequest } from '../../types/ingest'
import { IngestResultView } from './IngestResultView'
import { PriceChart } from './PriceChart'
import { useIngest } from './useIngest'
import { usePriceBars } from './usePriceBars'

const DEFAULTS = {
  symbol: 'AAPL',
  startDate: '2024-01-01',
  endDate: '2024-12-01',
}

// Date pickers give a YYYY-MM-DD; the backend wants an ISO timestamp.
const toIsoStartOfDay = (date: string): string => `${date}T00:00:00Z`

export function DataExplorerPage() {
  const queryClient = useQueryClient()
  const ingest = useIngest()
  const [symbol, setSymbol] = useState(DEFAULTS.symbol)
  const [startDate, setStartDate] = useState(DEFAULTS.startDate)
  const [endDate, setEndDate] = useState(DEFAULTS.endDate)
  // committedQuery is set on submit so the chart's useQuery doesn't fire on mount.
  const [committedQuery, setCommittedQuery] = useState<BarsQuery | null>(null)
  const priceBars = usePriceBars(committedQuery)

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const body: IngestRequest = {
      symbol: symbol.trim().toUpperCase(),
      start_date: toIsoStartOfDay(startDate),
      end_date: toIsoStartOfDay(endDate),
    }
    setCommittedQuery(body)
    ingest.mutate(body, {
      // Force the chart to refetch — the ingest just changed what's cached.
      onSuccess: () => queryClient.invalidateQueries({ queryKey: ['bars'] }),
    })
  }

  return (
    <section aria-label="data explorer" className="page data-explorer">
      <header>
        <h2>Data Explorer</h2>
        <p>Fetch and quality-check price bars for a symbol.</p>
      </header>

      <form onSubmit={onSubmit} className="ingest-form">
        <label>
          Symbol
          <input
            type="text"
            value={symbol}
            onChange={(event) => setSymbol(event.target.value)}
            required
          />
        </label>
        <label>
          Start date
          <input
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
            required
          />
        </label>
        <label>
          End date
          <input
            type="date"
            value={endDate}
            onChange={(event) => setEndDate(event.target.value)}
            required
          />
        </label>
        <button type="submit" disabled={ingest.isPending}>
          {ingest.isPending ? 'Ingesting…' : 'Ingest data'}
        </button>
      </form>

      {ingest.isError && (
        <p role="alert">Ingest failed — {(ingest.error as Error).message}</p>
      )}
      {ingest.data && <IngestResultView result={ingest.data} />}
      {priceBars.data && <PriceChart data={priceBars.data} />}
    </section>
  )
}
