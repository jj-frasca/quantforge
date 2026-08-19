import { Term } from '../../components/ui/Term'
import type { ValidationReport } from '../../types/validation'
import { RegimeBreakdownView } from './RegimeBreakdownView'

const asPercent = (value: number): string => `${(value * 100).toFixed(1)}%`
const asRatio = (value: number): string => value.toFixed(2)
// Reuse the IngestResultView's severity styles: good -> info chrome, warning -> warning,
// bad -> error. Keeps the visual language consistent across the app.
const verdictClass = (verdict: 'good' | 'warning' | 'bad'): 'info' | 'warning' | 'error' =>
  verdict === 'good' ? 'info' : verdict === 'warning' ? 'warning' : 'error'

interface Props {
  report: ValidationReport
}

export function ValidationReportView({ report }: Props) {
  return (
    <section aria-label="validation report" className={report.passed ? 'report pass' : 'report fail'}>
      <h2>{report.strategy_name}</h2>
      <p role="status" className="verdict">
        {report.passed ? 'Passes validation' : 'Does not pass validation'}
      </p>

      <dl className="metrics">
        <div>
          <dt>
            Observed{' '}
            <Term definition="Return per unit of risk — annualized mean return divided by annualized standard deviation. Above 1 is good; above 2 is excellent; below 0 means losing money on average.">
              Sharpe
            </Term>
          </dt>
          <dd>{asRatio(report.observed_sharpe)}</dd>
        </div>
        <div>
          <dt>
            <Term definition="The Sharpe ratio penalized for how many configurations we tried. Bailey & López de Prado (2014). DSR ≤ 0 means the result is plausibly explained by luck. DSR > 0 is necessary but NOT sufficient: measured against data with no edge by construction, this pipeline still produced a deflated Sharpe as high as +0.92, so the other criteria do the real work.">
              Deflated Sharpe
            </Term>
          </dt>
          <dd>{asRatio(report.deflated_sharpe)}</dd>
        </div>
        <div>
          <dt>
            <Term definition="Probability of Backtest Overfitting. Estimates how likely the in-sample result fails out-of-sample. Bailey et al. (2015). Below 0.3 is good; above 0.5 is high risk.">
              Probability of backtest overfitting
            </Term>
          </dt>
          <dd>{asPercent(report.pbo)}</dd>
        </div>
        <div>
          <dt>
            <Term definition="How robust the result is to small parameter tweaks. Above 0.7 means the strategy doesn't sit on a knife-edge; below 0.4 is fragile.">
              Parameter stability
            </Term>
          </dt>
          <dd>{asPercent(report.parameter_stability_score)}</dd>
        </div>
        <div>
          <dt>
            <Term definition="Re-pick the best configuration on each expanding training window, then score THAT choice on the window that follows, and average. Unlike the headline Sharpe it measures the selection procedure rather than one hand-picked config. ADR-038.">
              Walk-forward out-of-sample Sharpe
            </Term>
          </dt>
          <dd>
            {report.walk_forward ? (
              <>
                {asRatio(report.walk_forward.mean_oos_sharpe)}{' '}
                <span className="metric-hint">
                  (positive in {Math.round(report.walk_forward.consistency * report.walk_forward.n_splits)} of{' '}
                  {report.walk_forward.n_splits} windows)
                </span>
              </>
            ) : (
              <span className="metric-hint">not measured</span>
            )}
          </dd>
        </div>
        <div>
          <dt>
            <Term definition="How many purged cross-validation folds the sample supports — training rows within an embargo of the test block are removed (López de Prado 2018). This is the fold COUNT: the folds are not currently scored, see ADR-038.">
              Purged folds
            </Term>
          </dt>
          <dd>{report.n_purged_folds}</dd>
        </div>
      </dl>

      {report.interpretations.length > 0 && (
        <ul aria-label="interpretations" className="issues">
          {report.interpretations.map((item) => (
            <li key={item.metric} className={`issue ${verdictClass(item.verdict)}`}>
              <span className="check">{item.metric}</span>
              <span className="message">{item.message}</span>
            </li>
          ))}
        </ul>
      )}

      {report.flags.length > 0 && (
        <ul aria-label="flags" className="flags">
          {report.flags.map((flag) => (
            <li key={flag}>{flag}</li>
          ))}
        </ul>
      )}

      <RegimeBreakdownView breakdown={report.regime_breakdown} />
    </section>
  )
}
