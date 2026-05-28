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
under → short/flat.

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
