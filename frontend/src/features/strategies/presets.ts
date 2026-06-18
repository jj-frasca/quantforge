// "Try these first" preset configurations. Each is a one-click load of a canonical
// (symbol, strategy, params, window) setup for the Backtest Results form.
//
// Slate composition: three contrasting methodologies that pass cleanly + one "honest
// loser" (Triple MA) whose interest is its Validation report, not its backtest.

// `name` is the catalog discriminator; `params` carries the numeric tunables. Split
// rather than merged so TS strict doesn't object to a `string` value inside a
// `Record<string, number>`.
export interface Preset {
  id: string
  title: string
  subtitle: string
  description: string
  symbol: string
  yearsBack: number
  strategy: { name: string; params: Record<string, number> }
}

export const PRESETS: readonly Preset[] = [
  {
    id: 'sma-spy',
    title: 'SMA crossover on SPY',
    subtitle: 'SMA(50 / 200) · SPY · 5y',
    description:
      'The textbook "Golden Cross" trend-follower — buy when the 50-day average rises above the 200-day, sell when it falls back below.',
    symbol: 'SPY',
    yearsBack: 5,
    strategy: { name: 'sma', params: { fast: 50, slow: 200 } },
  },
  {
    id: 'rsi-aapl',
    title: 'RSI mean reversion on AAPL',
    subtitle: 'RSI(14, 30 / 70) · AAPL · 5y',
    description:
      'Pullback hunter — buy when RSI shows AAPL is oversold (RSI < 30) and sell when it is overbought (RSI > 70).',
    symbol: 'AAPL',
    yearsBack: 5,
    strategy: {
      name: 'rsi_mean_reversion',
      params: { window: 14, oversold: 30, overbought: 70 },
    },
  },
  {
    id: 'donchian-gld',
    title: 'Donchian breakout on GLD',
    subtitle: 'Donchian(20) · GLD · 5y',
    description:
      'Turtle-style breakout on gold — long when GLD makes a new 20-day high, flat otherwise.',
    symbol: 'GLD',
    yearsBack: 5,
    strategy: { name: 'donchian_breakout', params: { lookback: 20 } },
  },
  {
    id: 'triple-ma-qqq',
    title: 'Triple MA alignment on QQQ',
    subtitle: 'SMA(10 / 30 / 100) · QQQ · 5y · honest loser',
    description:
      'Long only when fast, medium, and slow averages all agree. The backtest may look tempting — open the Validation page to see whether it survives PBO and Deflated Sharpe.',
    symbol: 'QQQ',
    yearsBack: 5,
    strategy: {
      name: 'triple_ma_alignment',
      params: { fast: 10, medium: 30, slow: 100 },
    },
  },
]
