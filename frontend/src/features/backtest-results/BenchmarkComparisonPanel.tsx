import type { BenchmarkComparison } from '../../types/backtest'

const asPercent = (value: number): string => `${(value * 100).toFixed(1)}%`
const asRatio = (value: number): string => value.toFixed(2)

interface Props {
  comparison: BenchmarkComparison | null
}

// ADR-013: alpha/beta/IR against SPY. Absolute return is not the whole story — a positive
// return that is all beta is just leverage on the index. Alpha (risk-adjusted excess) drives
// the honest headline: "did you actually beat the market, or just ride it?"
export function BenchmarkComparisonPanel({ comparison }: Props) {
  if (comparison === null) return null

  const { benchmark_symbol: bench } = comparison
  // Verdict keys off the INFORMATION RATIO (risk-adjusted EXCESS return over the benchmark),
  // not CAPM alpha. Alpha can be positive on a money-losing strategy whose beta is negative,
  // which would read "beat SPY" on a strategy that lost money — the opposite of honest. IR is
  // "did you actually earn more than holding SPY, per unit of risk" — the question a user asks.
  const beat = comparison.information_ratio > 0
  return (
    <section aria-label="benchmark comparison" className="benchmark-comparison">
      <h3>vs. {bench}</h3>
      <p role="status" className={beat ? 'verdict pass' : 'verdict fail'}>
        {beat
          ? `This strategy beat ${bench} — it earned more than holding ${bench}, adjusted for the extra risk it took.`
          : `This strategy did not beat ${bench} — per unit of risk, you'd have done as well or better just holding ${bench}.`}
      </p>

      <dl className="metrics">
        <div>
          <dt>Alpha</dt>
          <dd>{asPercent(comparison.alpha)}</dd>
          <small className="metric-hint">
            Annualized return beyond what {bench} exposure alone would explain. Positive is
            real edge; zero or below means no value added over just holding {bench}.
          </small>
        </div>
        <div>
          <dt>Beta</dt>
          <dd>{asRatio(comparison.beta)}</dd>
          <small className="metric-hint">
            How much the strategy moves with {bench}. 1.0 = tracks it one-for-one; near 0 =
            largely independent of the market.
          </small>
        </div>
        <div>
          <dt>Information ratio</dt>
          <dd>{asRatio(comparison.information_ratio)}</dd>
          <small className="metric-hint">
            Excess return per unit of tracking risk — a Sharpe ratio measured against {bench}
            instead of cash. Above 0.5 is respectable.
          </small>
        </div>
        <div>
          <dt>Tracking error</dt>
          <dd>{asPercent(comparison.tracking_error)}</dd>
          <small className="metric-hint">
            How far the strategy's returns drift from {bench} year to year. Higher means a
            more different ride than the index.
          </small>
        </div>
        <div>
          <dt>Relative drawdown</dt>
          <dd>{asPercent(comparison.benchmark_relative_drawdown)}</dd>
          <small className="metric-hint">
            Worst stretch of underperformance vs. {bench} — the deepest you'd have lagged the
            index while holding this instead.
          </small>
        </div>
      </dl>
    </section>
  )
}
