import type { BacktestResponse } from '../../types/backtest'
import { BenchmarkComparisonPanel } from './BenchmarkComparisonPanel'
import { DrawdownChart } from './DrawdownChart'
import { EquityCurveChart } from './EquityCurveChart'
import { ReturnDistributionChart } from './ReturnDistributionChart'
import { RollingSharpeChart } from './RollingSharpeChart'

const asPercent = (value: number): string => `${(value * 100).toFixed(1)}%`
const asRatio = (value: number): string => value.toFixed(2)

interface Props {
  result: BacktestResponse
}

export function BacktestResultView({ result }: Props) {
  const positive = result.metrics.total_return >= 0
  return (
    <section
      aria-label="backtest result"
      className={positive ? 'report pass' : 'report fail'}
    >
      <h2>
        {result.strategy_name} · {result.symbol}
      </h2>
      <p role="status" className="verdict">
        Total return {asPercent(result.metrics.total_return)} over {result.equity_curve.length}{' '}
        bars; buy &amp; hold {asPercent(result.buy_and_hold_total_return)}
      </p>

      <dl className="metrics">
        <div>
          <dt>Sharpe</dt>
          <dd>{asRatio(result.metrics.sharpe)}</dd>
          {result.metrics.sharpe_ci && (
            <p className="metric-ci">
              95% CI: {asRatio(result.metrics.sharpe_ci.lower)} –{' '}
              {asRatio(result.metrics.sharpe_ci.upper)}
            </p>
          )}
          <small className="metric-hint">
            Return per unit of risk. Above 1 is good; above 2 is excellent; below 0
            means losing money on average.{' '}
            {result.metrics.sharpe_ci
              ? "The range beside it is how much this estimate could be off by sampling noise alone."
              : 'Under a year of history — too little data to show a confidence range.'}
          </small>
        </div>
        <div>
          <dt>Sortino</dt>
          <dd>{asRatio(result.metrics.sortino)}</dd>
          <small className="metric-hint">
            Like Sharpe, but only counts downside swings against you — upside spikes don't
            count as "risk".
          </small>
        </div>
        <div>
          <dt>Calmar</dt>
          <dd>{asRatio(result.metrics.calmar)}</dd>
          <small className="metric-hint">
            Annualized return divided by the worst drawdown. How much return you got for
            the deepest hole you'd have had to climb out of.
          </small>
        </div>
        <div>
          <dt>Annualized return</dt>
          <dd>{asPercent(result.metrics.annualized_return)}</dd>
          <small className="metric-hint">
            Compounded annual growth of this backtest. The S&P 500 has compounded at
            roughly 10% annually over long periods.
          </small>
        </div>
        <div>
          <dt>Annualized vol</dt>
          <dd>{asPercent(result.metrics.annualized_vol)}</dd>
          <small className="metric-hint">
            Year-over-year swings. Higher means a bumpier ride to the same destination.
          </small>
        </div>
        <div>
          <dt>Max drawdown</dt>
          <dd>{asPercent(result.metrics.max_drawdown)}</dd>
          <small className="metric-hint">
            Worst peak-to-trough drop. The deepest you'd have been down at any point.
          </small>
        </div>
        <div>
          <dt>Trades</dt>
          <dd>{result.n_trades}</dd>
          <small className="metric-hint">
            How often the strategy switched direction. More trades = more friction from
            costs.
          </small>
        </div>
        <div>
          <dt>Cost rate</dt>
          <dd>{asPercent(result.cost_rate)}</dd>
          <small className="metric-hint">
            Friction per trade. 10 bps = 0.10% per round-trip — eats away at high-turnover
            strategies.
          </small>
        </div>
      </dl>

      <EquityCurveChart
        data={result.equity_curve}
        benchmark={result.buy_and_hold_curve}
        benchmarkLabel={`Buy & hold ${result.symbol}`}
        tradeMarkers={result.trade_markers}
      />
      <BenchmarkComparisonPanel comparison={result.benchmark_comparison} />
      <DrawdownChart data={result.drawdown_curve} />
      <RollingSharpeChart
        data={result.rolling_sharpe_curve}
        window={result.rolling_sharpe_window}
      />
      <ReturnDistributionChart data={result.return_distribution} />
    </section>
  )
}
