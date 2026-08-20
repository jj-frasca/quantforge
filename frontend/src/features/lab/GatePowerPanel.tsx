import type { PowerCell, PowerSweep } from '../../types/lab'

const median = (values: number[]): number | null => {
  if (values.length === 0) {
    return null
  }
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid]
}

// The fraction of an available edge the catalog converts (ADR-045). An upper bound — the finalist
// is chosen in-sample — so a LOW value is the conclusive one.
const capture = (cell: PowerCell): number | null => {
  const oracle = median(cell.oracle_sharpes)
  const finalist = median(cell.finalist_observed_sharpes)
  if (oracle === null || finalist === null || oracle <= 0) {
    return null
  }
  return finalist / oracle
}

const label = (cell: PowerCell): string =>
  cell.phi !== null ? `phi ${cell.phi > 0 ? '+' : ''}${cell.phi}` : `half-life ${cell.half_life}`

const process = (edge: string): string =>
  edge === 'ar1' ? 'AR(1) on returns' : 'band reversion around a random-walk level'

// ADR-041/042/053. The panel above states how often the gate graduates something on data with no
// edge. This one states how often it finds an edge that IS there — the other half, and the one that
// decides whether "0 of 40 graduates clear the bar" is a fact about the strategies or about the
// gate. A visible Type-I error with no visible power number reads conservatism as strength.
export function GatePowerPanel({ sweeps }: { sweeps: PowerSweep[] }) {
  if (sweeps.length === 0) {
    return null
  }

  return (
    <section aria-label="gate power" className="deflation-headline">
      <h3>Measured detection rate</h3>
      {sweeps.map((sweep) => (
        <table key={sweep.edge}>
          <caption>
            {process(sweep.edge)} — a planted edge of measured strength, searched over{' '}
            {sweep.n_bars.toLocaleString('en-US')} bars, the same history a real hunt gets
          </caption>
          <thead>
            <tr>
              <th scope="col">Planted</th>
              <th scope="col">Oracle Sharpe</th>
              <th scope="col">Detected</th>
              <th scope="col">Clear the deflation bar</th>
              <th scope="col">Capture (upper bound)</th>
            </tr>
          </thead>
          <tbody>
            {sweep.cells.map((cell) => {
              const oracle = median(cell.oracle_sharpes)
              const captured = capture(cell)
              return (
                <tr key={label(cell)}>
                  <td>{label(cell)}</td>
                  <td>{oracle === null ? '—' : `${oracle >= 0 ? '+' : ''}${oracle.toFixed(2)}`}</td>
                  <td>{`${Math.round(cell.detection_rate * 100)}%`}</td>
                  <td>{`${cell.n_clear_deflation_bar} / ${cell.n_symbols}`}</td>
                  <td>{captured === null ? '—' : `${(captured * 100).toFixed(1)}%`}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      ))}
      <p data-testid="power-caveat">
        The planted edge is stationary and always on, so every rate here is an{' '}
        <strong>upper bound</strong> on power against real, intermittent edges. Capture is the
        fraction of the available edge the catalog converts, measured in-sample — so a{' '}
        <strong>low</strong> capture beside a zero detection rate points at the strategies, not at
        the thresholds.
      </p>
    </section>
  )
}
