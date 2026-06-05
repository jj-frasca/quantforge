# Research Papers (Cold Memory)

Citations with implementation summaries. Every strategy/validator cites a real paper in its
docstring and `research_citations`. Read when implementing research or validation components.

---

## Strategies

**Jegadeesh & Titman (1993)** — "Returns to Buying Winners and Selling Losers".
*Journal of Finance* 48(1), pp. 65–91.
- Momentum: rank by trailing return over a formation window (e.g. 3–12 months), go long past
  winners / short past losers, hold for a holding window. Implementation: signal from the sign
  of trailing return over a lookback, scaled to [-1, 1]. Skip the most recent period to avoid
  short-term reversal. Used by `MomentumStrategy`.

**Avellaneda & Lee (2010)** — "Statistical Arbitrage in the US Equities Market".
*Quantitative Finance* 10(7), pp. 761–782.
- Mean reversion: trade deviations from an equilibrium (z-score of price vs a rolling mean).
  Implementation: signal = −clip(z_score / k, −1, 1) so large positive deviations → short,
  large negative → long. Used by `MeanReversionStrategy`.

**SMA crossover** — no external citation required (textbook). Fast SMA over slow SMA → long;
under → short/flat. Used by `SMAStrategy`.

**Wilder, J. Welles (1978)** — *New Concepts in Technical Trading Systems*. Trend Research.
- Relative Strength Index (RSI). Implementation: SMA-style averaging of gains and losses over
  a trailing window (not Wilder's smoothed EMA — kept simple; switching to the smoothed variant
  is the "more aggressive" knob). `signal = +1` when RSI < `oversold`, `-1` when RSI >
  `overbought`, flat between. Edge cases: avg_loss == 0 with gains → RSI = 100 (pure uptrend);
  both zero → RSI is undefined and we treat it as neutral 50 so the strategy stays flat. No
  look-ahead via trailing `rolling(window).mean()`. Used by `RSIMeanReversionStrategy`.

**Faith, Curtis M. (2007)** — *Way of the Turtle*. McGraw-Hill.
- Donchian channel breakout (Dennis & Eckhardt's Turtle Trader rules, 1983–1988).
  Implementation: at bar *t*, compute the high and low of the PRIOR `lookback` bars
  (`close.shift(1).rolling(lookback).max()` and `.min()` — the shift is the no-look-ahead
  guarantee). `signal = +1` on a breakout above the channel high, `-1` below the channel low.
  Position carries forward between breakouts (`replace(0, NA).ffill()`) — the Turtle rule that
  makes the strategy actually trade-able rather than just signal at the instant of breakout.
  Used by `DonchianBreakoutStrategy`.

**Bollinger, John (2001)** — *Bollinger on Bollinger Bands*. McGraw-Hill.
- Bollinger Bands. Implementation: rolling mean +/- `num_std` * rolling sample std (ddof=1).
  Discrete signal — `+1` when close < lower band, `-1` when close > upper band, `0` between.
  Semantic cousin to the z-score `MeanReversionStrategy`: same hypothesis (price reverts to
  the rolling mean), different signal shape (discrete band crossing vs continuous z-clip).
  Constant-series degenerate case: rolling std collapses to 0 → bands collapse to the mean →
  signal stays flat. No look-ahead via trailing rolling windows. Used by `BollingerBandsStrategy`.

**Appel, Gerald (2005)** — *Technical Analysis: Power Tools for Active Investors*. FT Press.
- Moving Average Convergence Divergence (MACD). Implementation: MACD = EMA(close, fast) -
  EMA(close, slow); signal line = EMA(MACD, signal). Trading rule = sign of the histogram
  (`MACD - signal`): +1 when MACD above its signal line, -1 below. Implementation choice:
  `ewm(span, adjust=False)` — the recursive EMA convention. `adjust=True` (the pandas default)
  would use an equal-weighted formula until the window fills, which is NOT the conventional
  MACD definition and would silently shift the signal in the warmup region. EMA is causal by
  construction, so the no-look-ahead guarantee holds without an explicit `shift(1)`.
  Conventional Appel defaults: 12/26/9. Used by `MACDCrossoverStrategy`.

**Moskowitz, Ooi & Pedersen (2012)** — "Time Series Momentum".
*Journal of Financial Economics* 104(2), pp. 228-250.
- Vol-scaling for trend-following signals. Across 58 instruments the authors show that
  scaling position size by `target_vol / realized_vol` improves risk-adjusted return of
  momentum/trend signals: the underlying trend direction stays the same, the scaling
  moderates the contribution of high-vol regimes. Implementation: same fast/slow SMA
  crossover as `SMAStrategy` for the *direction*, then position SIZE =
  `clip(target_vol / realized_vol, upper=1.0).fillna(0.0)` so the strategy can only
  de-risk and never lever up. Realized vol is annualized via `sqrt(252)` on the rolling
  std of LOG returns — log returns are time-additive (clean rolling std) and symmetric
  (vol estimate doesn't drift with the price level). Used by `VolTargetedSMAStrategy`.
  This is the project's first strategy that does explicit risk management — separates
  *what to trade* from *how much to trade*, which most retail strategies conflate.

**Keltner, Chester W. (1960)** — *How To Make Money in Commodities*. Keltner Statistical
Service.
**Wilder, J. Welles (1978)** — *New Concepts in Technical Trading Systems*. Trend Research.
- Keltner Channel with Wilder's Average True Range. Implementation: midline =
  `close.ewm(span=ma_window, adjust=False).mean()` (modern EMA variant — Keltner's
  original used SMA; EMA is the standard today); width = `multiplier * ATR`. ATR uses
  the True Range definition from Wilder (1978): for each bar, the max of three
  quantities — (high - low), |high - prev_close|, |low - prev_close|. The shift(1) on
  prev_close is the no-look-ahead guarantee. ATR is the simple rolling mean of TR (the
  Wilder RMA, EMA with alpha=1/N, would be more traditional; SMA is easier to reason
  about and matches most charting platforms today). Signal: long on close > upper, short
  on close < lower, flat between — explicitly NO carry-forward (unlike Donchian, exiting
  a Keltner band is a normal occurrence). Used by `KeltnerChannelStrategy`. This is the
  project's first OHLC-using strategy — all earlier ones look only at close.

**Connors, Larry & Alvarez, Cesar (2009)** — *Short Term Trading Strategies That Work*.
TradingMarkets Publishing Group.
- Mean reversion *gated by* a longer-term trend filter. The book's signature setup is
  RSI(2) inside a 200-day SMA filter; we use a continuous z-score inside a
  configurable-window SMA filter because z-score composes naturally with the existing
  `MeanReversionStrategy` (same z math). The hypothesis: blind mean-reversion bets
  reliably catch falling knives during sustained moves; gating by the longer trend
  means we only buy oversold dips inside an uptrend (where mean reversion is empirically
  more reliable) and short rallies inside a downtrend. Implementation: two trailing
  rolling means (the z-score's `z_window` and the trend SMA's `trend_window`); a
  cross-parameter rule `trend_window > z_window` is enforced in the constructor — if
  the trend runs at the same horizon as the bet the strategy degenerates. Boolean
  masks for the four conditions (oversold, overbought, uptrend, downtrend) are
  `fillna(False)`-d so the warmup region stays flat rather than accidentally long via
  NaN-comparison weirdness. Used by `TrendFilteredMeanReversionStrategy`. This is the
  project's first multi-indicator strategy — the semantic move is *combination*
  (mean-reversion AND trend filter), the closest we have to strategy composition before
  a real DSL ships.

> The authoritative *list* of implemented strategies lives in `STRATEGY_CATALOG`
> (`backend/app/research/strategies/catalog.py`) and is served by `GET /api/v1/strategies`.
> This section is the *why* and the science — what each paper says and how we translated it
> to code, including the implementation trade-offs (which RSI variant; whether positions carry
> forward; what the degenerate cases are). See ADR-010 for the catalog pattern.

---

## Simulation

**Black & Scholes (1973)** — "The Pricing of Options and Corporate Liabilities".
*Journal of Political Economy* 81(3), pp. 637–654.
- Geometric Brownian Motion underlies the price process for the Monte Carlo simulator. GBM
  paths are strictly positive (a §8 invariant). Used by `MonteCarloSimulator`.

---

## Validation (Phase 4)

**Bailey, Borwein, López de Prado & Zhu (2015)** — "The Probability of Backtest Overfitting".
SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- PBO via Combinatorially-Symmetric Cross-Validation (CSCV): partition the returns matrix into
  S submatrices, evaluate in-sample vs out-of-sample rank of the selected configuration; PBO is
  the fraction of splits where the IS-best underperforms OOS-median. PBO ∈ [0, 1]; a random
  strategy gives ≈ 0.5.

**López de Prado (2018)** — *Advances in Financial Machine Learning*. Wiley. Ch. 7, 12.
- Purged K-Fold CV: when features/labels overlap in time, **purge** training samples whose
  labels overlap the test set and apply an **embargo** after each test fold to prevent leakage.
- Walk-forward: expanding/rolling train → test forward in time; never uses future data.

**Bailey & López de Prado (2014)** — "The Deflated Sharpe Ratio".
SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- DSR deflates the observed Sharpe for the number of trials, non-normality (skew/kurtosis),
  and sample length. **DSR ≤ observed Sharpe** always (a §8 invariant).
