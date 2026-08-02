import type { CrossSectionalView } from '../../types/lab'
import { useCrossSectional } from './useCrossSectional'

const fmt = (value: number): string => value.toFixed(2)
const fmtPct = (value: number): string => `${(value * 100).toFixed(0)}%`

export function CrossSectionalPanel() {
  const crossSectional = useCrossSectional()

  return (
    <section aria-label="cross-sectional section" className="lab-section">
      <h3>Cross-sectional hunt</h3>
      <p className="section-lede">
        A dollar-neutral long/short rank across the whole universe (ADR-024) — a per-strategy edge,
        not a single-name bet. The latest hunt and its graduation verdict.
      </p>
      {crossSectional.isPending && <p role="status">Loading cross-sectional hunt…</p>}
      {crossSectional.isError && (
        <p role="alert">
          Could not load the cross-sectional hunt — {(crossSectional.error as Error).message}
        </p>
      )}
      {/* data === null is a normal answer: no hunt has produced a record yet. */}
      {crossSectional.data === null && (
        <div className="cross-sectional empty">
          <p>No cross-sectional hunt has run yet — the pool is empty.</p>
        </div>
      )}
      {crossSectional.data != null && <CrossSectionalView view={crossSectional.data} />}
    </section>
  )
}

function CrossSectionalView({ view }: { view: CrossSectionalView }) {
  return (
    <div className="cross-sectional">
      <p className="summary">
        {view.universe_size} names ·{' '}
        {view.best_strategy_name ? `best: ${view.best_strategy_name}` : 'no ranked strategy'} ·{' '}
        <span className={`status-badge ${view.graduated ? 'pass' : 'muted'}`}>
          {view.graduated ? 'graduate' : 'no graduate'}
        </span>
        {view.graduated && view.graduate_holdout_sharpe != null && (
          <> · holdout Sharpe {fmt(view.graduate_holdout_sharpe)}</>
        )}
      </p>
      <div className="table-scroll">
        <table className="lab-table cross-sectional-table">
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Observed Sharpe</th>
              <th>Deflated Sharpe</th>
              <th>PBO</th>
              <th>Parameter stability</th>
            </tr>
          </thead>
          <tbody>
            {view.trials.map((trial) => (
              <tr
                key={trial.strategy_name}
                className={trial.strategy_name === view.best_strategy_name ? 'best' : undefined}
              >
                <td>{trial.strategy_name}</td>
                <td>{fmt(trial.observed_sharpe)}</td>
                <td>{fmt(trial.deflated_sharpe)}</td>
                <td>{fmtPct(trial.pbo)}</td>
                <td>{fmtPct(trial.parameter_stability_score)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
