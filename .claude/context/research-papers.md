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

**Elder, Alexander (1993)** — *Trading for a Living*. Wiley.
- Triple Screen / multi-condition trend confirmation. Elder's original method uses
  three different *timeframes* of the same indicator (weekly trend + daily oscillator
  + intraday entry). Our `TripleMAAlignmentStrategy` adapts the spirit (agreement
  before action) to a single timeframe via three SMA *windows*: long when
  `fast > medium > slow`, short when `fast < medium < slow`, flat otherwise. Cross-
  parameter rule `fast < medium < slow` enforced in the constructor. The stricter
  agreement rule (vs. a two-MA crossover) means fewer trades, longer holds, and an
  explicit flat state during chop. No look-ahead via trailing rolling means.

**Wilder, J. Welles (1978)** — *New Concepts in Technical Trading Systems*. Trend Research.
- ADX / DMI, traded as a regime signal: +DI/-DI (Wilder-smoothed directional movement over ATR)
  give direction, ADX (Wilder-smoothed DX) gives trend strength. Long when +DI > -DI AND ADX >
  `threshold`, short the symmetric case, flat when the trend is weak. All inputs are shifted/
  Wilder-smoothed — no look-ahead. Used by `ADXStrategy`.

**Lambert, Donald R. (1980)** — "Commodity Channel Index: Tools for Trading Cyclic Trends".
*Commodities* magazine.
- CCI, traded as mean reversion: (typical price - its rolling mean) / (0.015 * mean absolute
  deviation) — Lambert's 0.015 scaling puts ~70-80% of values in [-100, 100]. Long below
  -`threshold` (oversold), short above +`threshold`, flat between. Used by `CCIStrategy`.

**Chande, Tushar S. (1995)** — "Aroon". *Technical Analysis of Stocks & Commodities*.
- Aroon trend: Aroon-Up/-Down measure how recently the trailing window's high/low was made. Long
  when Aroon-Up > Aroon-Down (highs fresher than lows), short the reverse, flat when equal. Used
  by `AroonStrategy`.

**Kaufman, Perry J. (2013)** — *Trading Systems and Methods*. 5th ed. Wiley.
**Wilder, J. Welles (1978)** — *New Concepts in Technical Trading Systems*. Trend Research.
- ATR-channel breakout: an SMA midline +/- multiplier * Wilder ATR, trend-following like Donchian
  (position carries forward between breakouts) but volatility-scaled rather than fixed-width, so
  it widens in high-vol regimes and whipsaws less in chop. Used by `ATRChannelBreakoutStrategy`.

**Chande, Tushar S. & Kroll, Stanley (1994)** — *The New Technical Trader*. Wiley.
- Chande Momentum Oscillator, traded as mean reversion: like RSI but unsmoothed and symmetric in
  [-100, 100], so it swings to extremes faster. Long when CMO < -`threshold`, short when CMO >
  +`threshold`, flat between. Used by `ChandeMomentumStrategy`.

**Antonacci, Gary (2014)** — *Dual Momentum Investing: An Innovative Strategy for Higher Returns
with Lower Risk*. McGraw-Hill.
- Dual momentum, single-name proxy: long-only, requires BOTH absolute momentum (trailing return >
  0, i.e. beats cash) AND relative momentum (proxied here as close above its own longer trend SMA,
  since the original's cross-sectional ranking needs multiple names). The absolute-momentum gate
  is what sidesteps deep momentum drawdowns per Antonacci. Used by `DualMomentumStrategy`.

**Chaikin, Marc (1980s)** — Chaikin Money Flow; see Achelis, Steven B. *Technical Analysis A to
Z*. 2nd ed. McGraw-Hill, 2000.
- CMF: volume-weighted buying vs. selling pressure via the money-flow multiplier
  ((close-low)-(high-close))/(high-low), summed against volume over a trailing window. Long when
  CMF > `threshold` (net buying), short when CMF < -`threshold`, flat between. Used by
  `ChaikinMoneyFlowStrategy`.

**Coppock, Edwin S. (1962)** — "Practical Relative Strength Charting". *Barron's*.
- Coppock Curve: a linearly-weighted MA of two summed rate-of-change series, a slow momentum
  oscillator originally built to time major market bottoms (long-only, classic monthly params
  14/11/10). Generalized here to a symmetric trend sign: long above zero, short below. Used by
  `CoppockCurveStrategy`.

**Connors, Larry & Alvarez, Cesar (2009)** — *Short Term Trading Strategies That Work*.
TradingMarkets Publishing Group.
- Connors RSI: a very short (2-period) Wilder RSI traded at extreme thresholds (long below ~10,
  short above ~90) — a faster, more aggressive mean-reversion entry than the standard-window RSI
  strategy above. Used by `ConnorsRSIStrategy`.

**Faith, Curtis M. (2007)** — *Way of the Turtle*. McGraw-Hill.
**LeBeau, Charles & Lucas, David W. (1992)** — *Technical Traders Guide to Computer Analysis of
the Futures Markets*. Business One Irwin.
- Donchian channel entry with a Chandelier (ATR trailing-stop) exit rather than the opposite
  channel: while long, exit when close falls below the trailing high minus a multiple of ATR
  (and the mirror while short). The trailing stop lets a winner run while capping give-back —
  the Turtle system's edge over a symmetric-channel exit. Used by `DonchianATRTrailStrategy`.

**George, Thomas J. & Hwang, Chuan-Yang (2004)** — "The 52-Week High and Momentum Investing".
*Journal of Finance* 59(5), pp. 2145–2176.
- Proximity to the 52-week high (close / trailing window high) as a standalone momentum signal —
  stocks near their high keep outperforming because anchoring makes traders under-react to good
  news. Long near the high, short deep below it, flat in the band between. Used by
  `FiftyTwoWeekHighStrategy`.

**Crabel, Toby (1990)** — *Day Trading with Short Term Price Patterns and Opening Range
Breakout*. Traders Press. (Narrow-range / NR7, popularized by Linda Raschke.)
- Volatility-contraction breakout: after the narrowest-range bar in a trailing window, trade the
  direction it breaks (above the narrow bar's high → long, below its low → short). The only
  catalog strategy that trades a low→high volatility transition rather than a price level or
  moving average. Used by `NarrowRangeBreakoutStrategy`.

**Wilder, J. Welles (1978)** — *New Concepts in Technical Trading Systems*. Trend Research.
- A 2-signal COMBINATION: a classic fast/slow SMA crossover for direction, taken only when
  Wilder's ADX confirms a strong trend regime (ADX > `adx_threshold`); otherwise flat. The point
  is that an MA cross whipsaws in a range-bound (low-ADX) market — gating on trend strength sits
  those periods out. Used by `RegimeFilteredTrendStrategy`.

**Blitz, David, Huij, Joop & Martens, Martin (2011)** — "Residual Momentum". *Journal of
Empirical Finance* 18(3), pp. 506–521.
- Momentum computed on the part of returns NOT explained by systematic exposure is steadier and
  less crash-prone than raw price momentum. Single-name proxy (no market series available): the
  residual return is daily return minus its own trailing mean; signal is the sign of the summed
  residual over a lookback ending `skip` bars ago (skip avoids short-term reversal). Documented
  proxy — removes own-drift, not a true market beta. Used by `ResidualMomentumStrategy`.

**Lou, Dong, Polk, Christopher & Skouras, Spyros (2019)** — "A Tug of War: Overnight Versus
Intraday Expected Returns". *Journal of Financial Economics* 134(1).
- Overnight opens tend to partially reverse — fade the gap: short large up-gaps, long large
  down-gaps, flat for small gaps. Used by `OvernightGapStrategy`.

**Carter, John F. (2005)** — *Mastering the Trade*. McGraw-Hill.
- TTM squeeze: a "squeeze" is on when Bollinger Bands sit entirely inside Keltner Channels
  (range-based vol exceeds deviation-based vol — the coiled-spring compression); stand aside
  while it's on, and on release trade the direction of momentum (close vs. the shared midline)
  until the squeeze re-engages. Used by `SqueezeBreakoutStrategy`.

**Lane, George C. (1984)** — "Lane's Stochastics". *Technical Analysis of Stocks & Commodities*.
- Stochastic oscillator, traded as mean reversion: %K = position of close within the trailing
  high-low range; the smoothed %D crossing `oversold`/`overbought` thresholds triggers long/
  short, flat between. Used by `StochasticOscillatorStrategy`.

**Blau, William (1991)** — "True Strength Index". *Technical Analysis of Stocks & Commodities*;
also *Momentum, Direction, and Divergence*. Wiley, 1995.
- TSI: a double-smoothed (two chained EMAs) momentum oscillator scaled to [-100, 100] by the same
  double smoothing of absolute price change. The double pass strips most single-EMA noise, so the
  sign alone is traded — long when positive, short when negative. Used by
  `TrueStrengthIndexStrategy`.

**Williams, Larry (1979)** — *How I Made One Million Dollars Last Year Trading Commodities*.
Windsor Books.
- Williams %R, traded as mean reversion: position of close within the trailing high-low range,
  scaled to [-100, 0]. Long when %R < `oversold` (near the low), short when %R > `overbought`
  (near the high), flat between. Used by `WilliamsRStrategy`.

**Williams, Larry (1976)** — "The Ultimate Oscillator". *Technical Analysis of Stocks &
Commodities*.
- A three-timeframe (7/14/28) blend of buying-pressure-over-true-range averages, weighted 4:2:1,
  designed to cut the false divergences a single-window oscillator throws. Traded as mean
  reversion: long when oversold, short when overbought. Used by `UltimateOscillatorStrategy`.

**Berkowitz, Stephen A., Logue, Dennis E. & Noser, Eugene A. (1988)** — "The Total Cost of
Transactions on the NYSE". *Journal of Finance* 43(1).
- VWAP as an execution/fair-value benchmark, adapted here as a mean-reversion signal: long when
  close sits `threshold` below the rolling volume-weighted average price, short when above, flat
  between. Used by `VWAPReversionStrategy`.

**Moreira, Alan & Muir, Tyler (2017)** — "Volatility-Managed Portfolios". *Journal of Finance*
72(4), pp. 1611–1644.
- Scaling exposure by inverse realized VARIANCE (not volatility) raises a factor's risk-adjusted
  return: de-risk after variance spikes, lean in when calm. Direction is time-series momentum
  (sign of trailing return); size is `target_variance / realized_variance`, clipped to [0, 1] so
  the strategy can only de-risk, never lever up — the variance-exponent cousin of
  `VolTargetedSMAStrategy`'s inverse-volatility scaling. Used by `VolManagedMomentumStrategy`.

**Hutson, Jack K. (1983)** — "Good TRIX". *Technical Analysis of Stocks & Commodities* 1(5).
- TRIX: triple-smoothed (three chained EMAs) rate of change of the close, then signal-smoothed
  with one more EMA. The triple pass strips most short-cycle noise before the sign is traded —
  long when positive, short when negative, flat at zero. Used by `TRIXStrategy`.

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

## Metrics (backtesting/metrics.py)

**Sortino, Frank A. & van der Meer, Robert (1991)** — "Downside Risk: Capturing What's at Stake
in Investment Situations". *Journal of Portfolio Management* 17(4), pp. 27–31.
DOI: 10.3905/jpm.1991.409343
- Sortino ratio: divides excess return over a target by downside semi-deviation instead of total
  standard deviation, so upside dispersion is never charged against the strategy. Implementation
  squares only the shortfall below `target` and divides by the full sample size (the original
  definition), annualized via the same `sqrt(252)` convention as `sharpe_ratio`. Used by
  `sortino_ratio` (ADR-107), descriptive only — not a gate input.

**Young, Terry W. (1991)** — "Calmar Ratio: A Smoother Tool". *Futures* 20(12), p. 40.
- Calmar ratio: annualized return divided by the magnitude of max drawdown. A pure ratio of two
  already-computed `BacktestMetrics` fields, not a new estimate from a returns series. Used by
  `calmar_ratio` (ADR-108), descriptive only — not a gate input.

**Lo, Andrew W. (2002)** — "The Statistics of Sharpe Ratios". *Financial Analysts Journal* 58(4),
pp. 36–52. DOI: 10.2469/faj.v58.n4.2453
- Asymptotic standard error of an estimated Sharpe ratio under iid returns:
  `sqrt((1 + SR^2 / 2) / T)` per-period, annualized here as `sqrt((1 + SR^2 / 504) / years)`.
  Answers a different question than PBO/DSR (selection bias across a search): this is the
  sampling uncertainty in one already-observed Sharpe, given only the years of history available.
  Already load-bearing for the population-level detectable-edge frontier
  (`app/research/lab/frontier.py`, ADR-043); re-derived locally for the per-result case in
  `sharpe_confidence_interval` (ADR-109) since `backtesting/` sits below `lab/` in this
  codebase's layering and cannot import from it. `None` below 2 returns or below 1 year of data,
  where the asymptotic normal approximation is unreliable.

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
- The paper's DSR is a **probability**: PSR evaluated against the expected maximum Sharpe across
  trials. It incorporates the number and variance of trials plus the selected strategy's sample
  length, skewness, and kurtosis. QuantForge currently stores a value-form selection-adjusted
  Sharpe margin instead; FINDING-007 records that source mismatch. The local invariant
  `margin <= observed Sharpe` is not an invariant of the paper's probability statistic.

**Efron (1979)** — "Bootstrap Methods: Another Look at the Jackknife".
*Annals of Statistics* 7(1), pp. 1–26. DOI: https://doi.org/10.1214/aos/1176344552
- The empirical distribution is resampled at the observation's actual dimension. For ADR-081 the
  observation is one complete same-day cross-sectional return vector, not one scalar symbol return;
  resampling vector rows preserves contemporaneous dependence inside a draw.

**Politis & Romano (1994)** — "The Stationary Bootstrap".
*Journal of the American Statistical Association* 89(428), pp. 1303–1313.
- Resampling time blocks is appropriate when inference should retain weak serial dependence. It is
  deliberately not ADR-081's no-edge generator: retaining blocks can retain the momentum/reversion
  structure the catalog searches. ADR-081 samples complete vector rows iid instead.
