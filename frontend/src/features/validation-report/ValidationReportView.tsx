import type { ValidationReport } from '../../types/validation'

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
          <dt>Observed Sharpe</dt>
          <dd>{asRatio(report.observed_sharpe)}</dd>
        </div>
        <div>
          <dt>Deflated Sharpe</dt>
          <dd>{asRatio(report.deflated_sharpe)}</dd>
        </div>
        <div>
          <dt>Probability of backtest overfitting</dt>
          <dd>{asPercent(report.pbo)}</dd>
        </div>
        <div>
          <dt>Parameter stability</dt>
          <dd>{asPercent(report.parameter_stability_score)}</dd>
        </div>
        <div>
          <dt>Walk-forward splits</dt>
          <dd>{report.n_walk_forward_splits}</dd>
        </div>
        <div>
          <dt>Purged folds</dt>
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
    </section>
  )
}
