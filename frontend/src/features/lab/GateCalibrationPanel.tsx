import type { NullCalibration } from '../../types/lab'

const asPercent = (value: number): string => `${(value * 100).toFixed(2)}%`

const historyBars = (calibration: NullCalibration): number | null => {
  if (calibration.n_bars.length === 0) {
    return null
  }
  const values = [...calibration.n_bars].sort((a, b) => a - b)
  return values[Math.floor(values.length / 2)]
}

// ADR-036/037. Every other number on this page describes how the gate judged real symbols. This one
// describes how often the same gate graduates something on data with NO EDGE by construction —
// the only number here that bounds how much the rest can be trusted.
export function GateCalibrationPanel({ calibrations }: { calibrations: NullCalibration[] }) {
  if (calibrations.length === 0) {
    return null
  }
  const worstDsr = Math.max(...calibrations.map((c) => c.max_deflated_sharpe))

  return (
    <section aria-label="gate calibration" className="deflation-headline">
      <h3>Measured false-graduation rate</h3>
      <table>
        <caption>
          The unmodified search and gate, run over synthetic symbols with no edge by construction
        </caption>
        <thead>
          <tr>
            <th scope="col">Null model</th>
            <th scope="col">History</th>
            <th scope="col">Symbols</th>
            <th scope="col">False graduates</th>
            <th scope="col">Type-I error</th>
            <th scope="col">Clear the deflation bar</th>
            <th scope="col">Search version</th>
          </tr>
        </thead>
        <tbody>
          {calibrations.map((c) => {
            const history = historyBars(c)
            return (
              <tr key={`${c.null_mode}-${history ?? 'legacy'}`}>
                <td>{c.null_mode}</td>
                <td>{history === null ? 'legacy' : history.toLocaleString('en-US')}</td>
                <td>{c.n_symbols.toLocaleString('en-US')}</td>
                <td>{c.n_graduates}</td>
                <td>{asPercent(c.false_graduation_rate)}</td>
                <td>{c.n_clear_deflation_bar}</td>
                <td title={c.search_config_version}>
                  {c.search_config_version === 'legacy-unspecified'
                    ? 'legacy'
                    : c.search_config_version.slice(0, 8)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p data-testid="dsr-caveat">
        On this same edge-free data the pipeline still produced a deflated Sharpe as high as{' '}
        <strong>{worstDsr.toFixed(2)}</strong>. A positive deflated Sharpe is therefore necessary but{' '}
        <strong>not sufficient</strong> — the other criteria (PBO, MinTRL, the locked holdout, and
        beating buy-and-hold) are what hold the error rate down.
      </p>
    </section>
  )
}
