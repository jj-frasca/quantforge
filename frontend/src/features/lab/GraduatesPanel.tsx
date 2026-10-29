import type { GraduateRow } from '../../types/lab'
import { useGraduates } from './useGraduates'

const fmtSharpe = (value: number | null | undefined): string =>
  value === null || value === undefined ? '—' : value.toFixed(2)

const fmtScore = (value: number | null | undefined): string =>
  value === null || value === undefined ? '—' : `${(value * 100).toFixed(0)}%`

const formatRecordedRate = new Intl.NumberFormat('en-US', {
  style: 'percent', maximumSignificantDigits: 6,
})

function RecordedDcfSettings({ settings }: { settings: GraduateRow['dcf_assumptions'] }) {
  if (settings === null || settings === undefined) {
    return <p className="dcf-settings-unknown">DCF settings not recorded</p>
  }
  return (
    <details className="recorded-dcf-settings">
      <summary>Recorded DCF settings</summary>
      <dl>
        <dt>Discount rate</dt><dd>{formatRecordedRate.format(settings.discount_rate)}</dd>
        <dt>Terminal growth</dt><dd>{formatRecordedRate.format(settings.terminal_growth)}</dd>
        <dt>Minimum growth bound</dt><dd>{formatRecordedRate.format(settings.min_growth)}</dd>
        <dt>Maximum growth bound</dt><dd>{formatRecordedRate.format(settings.max_growth)}</dd>
        <dt>Projection years</dt><dd>{settings.projection_years}</dd>
      </dl>
      <p>Recorded settings alone do not reproduce or validate the score. Settings may not have
        affected an unsuccessful DCF.</p>
    </details>
  )
}

// Universe-deflation verdict (ADR-018) is the honest caveat on a graduate: does its holdout Sharpe
// clear the best-of-N-under-the-null bar, or is it plausibly just cross-symbol selection luck?
function deflationLabel(row: GraduateRow): string {
  if (row.survives_universe_deflation === null || row.survives_universe_deflation === undefined) {
    return '—'
  }
  return row.survives_universe_deflation ? 'survives' : 'selection-lucky'
}

export function GraduatesPanel() {
  const graduates = useGraduates()

  return (
    <section aria-label="graduates section" className="lab-section">
      <h3>Graduates — strategies that cleared the gate</h3>
      <p className="section-lede">
        Every experiment below survived the full graduation gate — Deflated Sharpe, PBO, parameter
        stability, MinTRL, and a locked out-of-sample holdout it could not see during the search.
      </p>
      {graduates.isPending && <p role="status">Loading graduates…</p>}
      {graduates.isError && (
        <p role="alert">Could not load graduates — {(graduates.error as Error).message}</p>
      )}
      {graduates.data && <GraduatesTable rows={graduates.data} />}
    </section>
  )
}

function GraduatesTable({ rows }: { rows: GraduateRow[] }) {
  if (rows.length === 0) {
    return (
      <div className="graduates empty">
        <p>No graduates yet — no strategy has cleared the gate. The bar is unforgiving by design.</p>
      </div>
    )
  }

  const nSurvive = rows.filter((r) => r.survives_universe_deflation === true).length

  return (
    <div className="graduates">
      <p className="summary">
        {rows.length} graduate{rows.length === 1 ? '' : 's'} · {nSurvive} survive
        {nSurvive === 1 ? 's' : ''} universe deflation
      </p>
      <div className="table-scroll">
        <table className="lab-table graduates-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Strategy</th>
              <th>Deflated Sharpe</th>
              <th>Holdout Sharpe</th>
              <th>Universe deflation</th>
              <th>Undervaluation</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.symbol}-${row.strategy_name}`} className="graduated">
                <td>{row.symbol}</td>
                <td>{row.strategy_name}</td>
                <td>{fmtSharpe(row.deflated_sharpe)}</td>
                <td>{fmtSharpe(row.holdout_sharpe)}</td>
                <td>
                  <span
                    className={`status-badge ${
                      row.survives_universe_deflation ? 'pass' : 'muted'
                    }`}
                  >
                    {deflationLabel(row)}
                  </span>
                </td>
                <td>
                  <div className="graduate-valuation">
                    <span>{fmtScore(row.undervaluation_score)}</span>
                    <RecordedDcfSettings settings={row.dcf_assumptions} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
