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
          <small className="metric-hint">
            Return per unit of risk. Above 1 is good; above 2 is excellent; below 0
            means losing money on average.
          </small>
        </div>
        <div>
          <dt>Annualized return</dt>
          <dd>{asPercent(result.metrics.annualized_return)}</dd>
          <small className="metric-hint">
            What this would have averaged per year. The S&P 500 has averaged ~10%
            historically.
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
