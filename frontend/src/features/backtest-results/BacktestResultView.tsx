import type { BacktestResponse } from '../../types/backtest'
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
        </div>
        <div>
          <dt>Annualized return</dt>
          <dd>{asPercent(result.metrics.annualized_return)}</dd>
        </div>
        <div>
          <dt>Annualized vol</dt>
          <dd>{asPercent(result.metrics.annualized_vol)}</dd>
        </div>
        <div>
          <dt>Max drawdown</dt>
          <dd>{asPercent(result.metrics.max_drawdown)}</dd>
        </div>
        <div>
          <dt>Trades</dt>
          <dd>{result.n_trades}</dd>
        </div>
        <div>
          <dt>Cost rate</dt>
          <dd>{asPercent(result.cost_rate)}</dd>
        </div>
      </dl>

      <EquityCurveChart
        data={result.equity_curve}
        benchmark={result.buy_and_hold_curve}
        benchmarkLabel={`Buy & hold ${result.symbol}`}
        tradeMarkers={result.trade_markers}
      />
      <DrawdownChart data={result.drawdown_curve} />
      <RollingSharpeChart
        data={result.rolling_sharpe_curve}
        window={result.rolling_sharpe_window}
      />
      <ReturnDistributionChart data={result.return_distribution} />
    </section>
  )
}
