import type { CrossSectionalTrial, CrossSectionalView } from '../../types/lab'
import { useCrossSectional } from './useCrossSectional'

const fmt = (value: number): string => value.toFixed(2)
const fmtPct = (value: number): string => `${(value * 100).toFixed(0)}%`
// A real factor's mean IC is ~0.02-0.05, so two decimals would round most of them to 0.00.
const fmtIc = (value: number | null | undefined, digits: number): string =>
  value == null ? '—' : value.toFixed(digits)

export function CrossSectionalPanel() {
  const crossSectional = useCrossSectional()

  return (
    <section aria-label="cross-sectional section" className="lab-section">
      <h3>Cross-sectional hunt</h3>
      <p className="section-lede">
        A dollar-neutral long/short rank across the whole universe (ADR-024) — a per-strategy edge,
        not a single-name bet. The latest hunt and its graduation verdict. Rank IC (ADR-035) is a
        diagnostic, not a gate: it says whether the ranking itself carried information, which a
        portfolio Sharpe cannot distinguish from two lucky names.
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
      {view.walk_forward_method != null && (
        <p className="section-lede">
          Family walk-forward: equal mean of same-window equal-weight universe benchmark Sharpes:{' '}
          {fmt(view.walk_forward_hold_sharpe!)} · {view.walk_forward_n_bars} search bars ·{' '}
          {view.walk_forward_n_splits} windows. Selection within each family uses earlier training rows.
        </p>
      )}
      <div className="table-scroll">
        <table className="lab-table cross-sectional-table">
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Observed Sharpe</th>
              <th>Deflated Sharpe</th>
              <th>PBO</th>
              <th>Parameter stability</th>
              <th>Walk-forward mean Sharpe</th>
              <th>Purged CV mean Sharpe</th>
              <th>Mean rank IC</th>
              <th>IC t-stat</th>
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
                <td>
                  {trial.walk_forward_oos_sharpe == null
                    ? 'not measured'
                    : `${fmt(trial.walk_forward_oos_sharpe)}${view.walk_forward_method == null ? ' · legacy, unpaired' : ''}`}
                </td>
                <td><PurgedDiagnostic trial={trial} /></td>
                <td>{fmtIc(trial.ic_mean, 3)}</td>
                <td>{fmtIc(trial.ic_t_stat, 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="section-lede">
        Attributed walk-forward diagnostics are family-local: the winning family uses the complete
        search sample. Continued
        configurations include internal costs; account entry and switching trades are not reconciled.
        The equal-weight universe benchmark adds no turnover-cost model. Supplied fundamental inputs
        are static snapshots, not historical point-in-time information. Scores are equal means of
        window Sharpes, not Sharpe on stitched policy returns. Purged CV support is restricted to audited family recipes
        (including audited direct-shift recipes); later training is intentional.
        Purged CV scores are equal means of retained-fold Sharpes, paired with each family’s
        same-kept-fold equal-weight universe benchmark, not Sharpe on stitched policy returns.
      </p>
    </div>
  )
}


function PurgedDiagnostic({ trial }: { trial: CrossSectionalTrial }) {
  const evidence = trial.purged_diagnostic
  if (evidence == null) {
    return trial.purged_cv_oos_sharpe == null
      ? <>not measured</>
      : <>{fmt(trial.purged_cv_oos_sharpe)} · legacy, unpaired</>
  }
  if (evidence.status === 'unsupported') {
    const reasons = {
      unsupported_factory: 'unsupported or custom recipe',
      unsupported_parameters: 'unsupported parameters',
      unsupported_price_dtype: 'unsupported price format',
      unsupported_pandas_version: 'unsupported pandas version',
      unsupported_rolling_engine: 'unsupported rolling engine',
    }
    return <>not measured · {reasons[evidence.reason!]}</>
  }
  return (
    <>
      {evidence.status === 'measured' ? (
        <>
          <span>{fmt(evidence.mean_oos_sharpe!)}</span>
          <p>Same-kept-fold equal-weight universe benchmark: {fmt(evidence.mean_oos_hold_sharpe!)}</p>
        </>
      ) : <span>not measured · no usable folds</span>}
      <details>
        <summary>Fold evidence</summary>
        {evidence.method === 'restricted-pandas-3.0.6-cython-high-purged-equal-weight-continuation-v2' && (
          <p>Recipe qualification: pandas 3.0.6 Cython trailing-high on complete native Float64 panels.</p>
        )}
        <p>{evidence.n_bars} search bars · {evidence.kept_fold_ordinals!.length} of {evidence.requested_folds} folds kept</p>
        <p>Original floor: {evidence.floor} · allocated price lag: {evidence.max_price_lag} · embargo: {evidence.embargo}</p>
        {evidence.kept_fold_ordinals!.length > 0 && (
          <p>Kept fold numbers: {evidence.kept_fold_ordinals!.map((j) => j + 1).join(', ')}</p>
        )}
      </details>
    </>
  )
}
