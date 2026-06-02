import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { BarsResponse } from '../../types/bars'

interface Props {
  data: BarsResponse
}

// Closes-over-time line chart. The DataQualityEngine has already vetted the bars
// (cache-aside flow ingests through the quality gate), so we don't filter here.
export function PriceChart({ data }: Props) {
  if (data.n_bars === 0) {
    return (
      <section aria-label="price chart" className="price-chart empty">
        <p>No cached bars for this range. Run an ingest above.</p>
      </section>
    )
  }

  const chartData = data.bars.map((bar) => ({
    date: bar.timestamp_utc.slice(0, 10),
    close: bar.close,
  }))
  const lastClose = data.bars[data.bars.length - 1].close

  return (
    <section aria-label="price chart" className="price-chart">
      <p className="summary">
        {data.n_bars} bars · last close {lastClose.toFixed(2)}
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" minTickGap={32} />
          <YAxis domain={['auto', 'auto']} />
          <Tooltip />
          <Line type="monotone" dataKey="close" stroke="#22c55e" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </section>
  )
}
