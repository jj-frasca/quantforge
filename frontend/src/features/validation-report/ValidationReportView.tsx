import { Term } from '../../components/ui/Term'
import type { ValidationReport } from '../../types/validation'
import { RegimeBreakdownView } from './RegimeBreakdownView'

const asPercent = (value: number): string => `${(value * 100).toFixed(1)}%`
const asRatio = (value: number): string => value.toFixed(2)
// ADR-068: an excess is a difference, so it is only legible with its sign.
const asSigned = (value: number): string => (value >= 0 ? `+${value.toFixed(2)}` : value.toFixed(2))
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
            <Term definition="The observed Sharpe minus a penalty for how many configurations we tried, in Sharpe units — a selection-adjusted MARGIN adapted from Bailey & López de Prado (2014), not the paper's probability-form DSR, which also uses the track record's length, skewness and kurtosis (ADR-054). At or below 0 the result is plausibly explained by luck. Above 0 is necessary but NOT sufficient: measured against data with no edge by construction, this pipeline still produced a margin as high as +0.92, so the other criteria do the real work.">
              Selection-adjusted Sharpe margin
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
                {typeof report.walk_forward.mean_oos_hold_sharpe === 'number' && (
                  <div className="metric-hint" data-testid="walk-forward-hold">
                    Holding the same windows earned{' '}
                    {asRatio(report.walk_forward.mean_oos_hold_sharpe)} —{' '}
                    {asSigned(
                      report.walk_forward.mean_oos_sharpe - report.walk_forward.mean_oos_hold_sharpe,
                    )}{' '}
                    over holding
                  </div>
                )}
              </>
            ) : (
              <span className="metric-hint">not measured</span>
            )}
          </dd>
        </div>
        <div>
          <dt>
            <Term definition="Each fold is scored by the config chosen on the remaining rows, with rows within an embargo of the fold removed so a rolling window cannot straddle the boundary (López de Prado 2018). Unlike walk-forward this is NOT causal — the training rows include data from after the fold — so read it as how stable the edge is across regimes, not as what you would have earned. ADR-039.">
              Purged-CV out-of-sample Sharpe
            </Term>
          </dt>
          <dd>
            {report.purged_cv ? (
              <>
                {asRatio(report.purged_cv.mean_oos_sharpe)}{' '}
                <span className="metric-hint">
                  (± {asRatio(report.purged_cv.oos_sharpe_std)} across {report.purged_cv.n_folds}{' '}
                  folds, {report.purged_cv.embargo}-bar embargo)
                </span>
              </>
            ) : (
              <span className="metric-hint">{report.n_purged_folds} folds, not scored</span>
            )}
          </dd>
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
