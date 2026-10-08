import type { PowerCell, PowerSweep } from '../../types/lab'

const median = (values: number[]): number | null => {
  if (values.length === 0) {
    return null
  }
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid]
}

const sharpe = (value: number | null): string =>
  value === null ? '—' : `${value >= 0 ? '+' : ''}${value.toFixed(2)}`

const percent = (value: number | null): string =>
  value === null ? '—' : `${(value * 100).toFixed(1)}%`

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
            {sweep.edge === 'ar1' && (
              <p>
                AR(1) scores use the historical reference sign strategy, which omits the drift
                intercept; these are not conditional-mean optimal or realized-sample maximum Sharpes.
              </p>
            )}
            {sweep.edge === 'band_reversion' && (
              <p>
                Band scores use historical latent and filtered sign references. Their positions
                use predicted log returns while their scores use simple returns; these do not
                certify an optimal strategy before or after costs, or a maximum sample Sharpe.
              </p>
            )}
          </caption>
          <thead>
            <tr>
              <th scope="col">Planted</th>
              <th scope="col">{
                sweep.edge === 'ar1' ? 'Reference Sharpe' :
                  sweep.edge === 'band_reversion' ? 'Latent reference Sharpe' : 'Oracle Sharpe'
              }</th>
              <th scope="col">{
                sweep.edge === 'ar1' ? 'Reference net of costs' :
                  sweep.edge === 'band_reversion' ? 'Latent reference net of costs' : 'Oracle net of costs'
              }</th>
              <th scope="col">Detected</th>
              <th scope="col">Clear the deflation bar</th>
              <th scope="col">Capture (in-sample)</th>
              <th scope="col">Capture, net</th>
              <th scope="col">{sweep.edge === 'band_reversion' ? 'Filtered reference Sharpe' : 'Oracle a filter could form'}</th>
              <th scope="col">{sweep.edge === 'band_reversion' ? 'Capture vs filtered reference' : 'Capture vs achievable'}</th>
            </tr>
          </thead>
          <tbody>
            {sweep.cells.map((cell) => {
              return (
                <tr key={label(cell)}>
                  <td>{label(cell)}</td>
                  <td>{sharpe(median(cell.oracle_sharpes))}</td>
                  <td>{sharpe(median(cell.net_oracle_sharpes))}</td>
                  <td>{`${Math.round(cell.detection_rate * 100)}%`}</td>
                  <td>{`${cell.n_clear_deflation_bar} / ${cell.n_symbols}`}</td>
                  <td>{percent(cell.capture_ratio)}</td>
                  <td>{percent(cell.net_capture_ratio)}</td>
                  <td>{sharpe(median(cell.achievable_oracle_sharpes))}</td>
                  <td>{percent(cell.achievable_capture_ratio)}</td>
                </tr>
              )
            })}
            {sweep.cells.map((cell) => {
              const split = Object.entries(cell.net_capture_by_category)
              if (split.length === 0) {
                return null
              }
              return (
                <tr key={`${label(cell)}-split`} data-testid="capture-by-category">
                  <td colSpan={9}>
                    {label(cell)} — net capture by category:{' '}
                    {split
                      .sort(([a], [b]) => a.localeCompare(b))
                      .map(([category, ratio]) => `${category} ${percent(ratio)}`)
                      .join(' · ')}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      ))}
      <p data-testid="power-caveat">
        These stationary, always-on synthetic controls do not establish a bound on real-market
        power. Capture is the
        in-sample finalist Sharpe relative to the stated reference; selection can inflate this
        ratio. The sign reference trades constantly, so read the{' '}
        <strong>net</strong> columns: they charge it the same costs every catalog finalist paid,
        while a near-zero net reference cannot support a stable capture ratio and does not establish
        that no tradeable edge exists. For band reversion, the filtered reference uses prices;
        the latent reference knows the hidden state. A near-zero filtered net reference does not
        establish that no recoverable edge exists.
      </p>
    </section>
  )
}
