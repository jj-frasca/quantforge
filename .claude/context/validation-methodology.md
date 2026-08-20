# Validation Methodology (Cold Memory)

Formal specs for the validation engine (Phase 4) — the layer that makes QuantForge credible.
Read when working on `backend/app/validation/`. Citations + summaries in research-papers.md.
Each component encodes a mathematical invariant as a Hypothesis property test.

---

## 1. Deflated Sharpe Ratio (DSR) — value form

`app/validation/deflated_sharpe.py`. Bailey & López de Prado (2014).

We report DSR as a **deflated Sharpe value** (not a probability), so the §8 invariant
**DSR ≤ observed Sharpe** holds by construction: `DSR = observed_SR - haircut`, where the
haircut is the expected maximum Sharpe under the null of N independent trials:

```
# Expected max of N iid ~N(0, sr_std^2) Sharpe estimates (Bailey et al.):
E_max = sr_std * ((1 - γ) * Φ⁻¹(1 - 1/N) + γ * Φ⁻¹(1 - 1/(N·e)))      # γ = Euler-Mascheroni 0.5772
haircut = max(E_max, 0)        # N == 1 -> haircut 0 (no multiple-testing penalty)
DSR = observed_sr - haircut
```

- `sr_std`: dispersion of Sharpe across trials (input; default a small positive value).
- **Invariant**: `DSR ≤ observed_sr` always (haircut ≥ 0); more trials ⇒ larger haircut ⇒
  lower (or equal) DSR; N == 1 ⇒ DSR == observed_sr.

**Search-level accounting (ADR-046).** A StrategyLab run first evaluates parameter configs inside
families and then selects across the family finalists. DSR must price that whole selection, not
reset inside each family. Both longitudinal and cross-sectional search pool every current candidate
Sharpe to estimate one `sr_std`, use cumulative concrete-config `lifetime_trials` for N, and apply
the same haircut to every family finalist before the overall argmax. `Trial` is therefore a compact
family-finalist summary with `n_evaluated_configs`; the number of stored summaries is NOT the DSR or
MinTRL denominator. Historical longitudinal pool counters predate this field and remain a lower
bound; generated records are never guessed/backfilled against today's catalog.

---

## 2. Probability of Backtest Overfitting (PBO) — CSCV

`app/validation/pbo.py`. Bailey et al. (2015), Combinatorially-Symmetric Cross-Validation.

Input: a performance matrix `R` of shape (T observations, N configurations). Procedure:
1. Split the T rows into `S` disjoint groups (S even).
2. For each of the C(S, S/2) ways to pick S/2 groups as **in-sample (IS)** (rest = OOS):
   - rank configs by IS Sharpe; pick the IS-best `n*`.
   - compute the OOS rank of `n*` as `w = rank / (N + 1)` ∈ (0, 1).
   - `logit = ln(w / (1 - w))`; the split is "overfit" if `logit ≤ 0` (IS-best below OOS median).
3. **PBO = fraction of splits that are overfit.**

- **Invariant**: PBO ∈ [0, 1]. A matrix of pure-noise configs ⇒ PBO ≈ 0.5; a single
  dominant config ⇒ PBO ≈ 0.

---

## 3. Walk-forward evaluation (ADR-038)

`app/validation/walk_forward.py`. Expanding window: train on [0, k), test on the next block,
step forward. `walk_forward_splits` returns `list[(train_idx, test_idx)]`;
`walk_forward_evaluate(performance, splits)` then **selects the train-block argmax config and
scores it on the following test block**, returning `mean_oos_sharpe`, `consistency` (share of
windows with a positive OOS Sharpe) and Pardo `efficiency`.

This is the only *causal* out-of-sample number in the system besides the locked holdout, and unlike
the holdout it measures the **selection procedure** rather than one config chosen on the whole
sample. It reuses the (T, N) matrix PBO already builds — valid because every catalog strategy is
causal — so it costs no extra backtests. Sharpes are annualized, like everything else.

- **Invariant**: `max(train_idx) < min(test_idx)` for every split — never uses future data.
- **Invariant**: a split's selection depends only on its own train rows. Stated PER SPLIT: the
  train window EXPANDS, so a later split legitimately absorbs an earlier split's test rows.
- `efficiency` is `None` when mean in-sample Sharpe ≤ 0 — a ratio of two negative Sharpes is
  positive and would read as "efficient" while both halves lost money.
- **Measured under the null (2026-08-19, N=200/mode):** median +0.15 (iid) / +0.33 (bootstrap:SPY),
  p95 +0.78 / +1.05. **Below ~1.0 is indistinguishable from noise.** The bootstrap null sits higher
  because the selection earns *drift*, so any future gate on this must be stated against
  buy-and-hold on the same windows, never against zero (ADR-038 §Measured).

---

## 4. Purged K-Fold CV (ADR-039)

`app/validation/purged_cv.py`. López de Prado (2018) ch. 7. K folds; for each test fold, **purge**
training indices within `embargo` of the test fold (overlapping labels leak), and apply the
embargo after the test block. `purged_cv_evaluate` then selects on the purged train rows and
scores that choice on the fold, reporting the mean, the **dispersion across folds**, consistency
and the embargo used.

`lookback_embargo(configs, floor)` sizes the embargo from the grid's largest integer parameter (a
documented proxy for the longest window) rather than a constant — the old fixed `embargo=2` purged
~1% of the contaminated region for a 200-bar strategy.

**Read it NEXT TO walk-forward, never instead of it.** A fold's training rows include data from
*after* its test block, so purged CV is not causal: it measures how stable an edge is across
regimes with boundary leakage removed, not what the procedure would have earned. Measured under
the null it scores systematically ABOVE walk-forward (median +0.26 / +0.39; p95 +0.88 / +1.06) —
that gap IS the optimistic bias, and it is why the two are never averaged.

- **Invariant**: no training index lies within `embargo` of any test index (no leakage).
- A sample too short to hold the folds plus an honest embargo reports `purged_cv=None` plus a
  flag. Shrinking the embargo to fit would emit a leaky number labelled "purged".

---

## 5. ValidationReport

`app/validation/report.py` — Pydantic model aggregating the above for one strategy:
`strategy_name`, `observed_sharpe`, `deflated_sharpe`, `pbo`, `n_walk_forward_splits`,
`n_purged_folds`, `walk_forward` (ADR-038) and `purged_cv` (ADR-039) — both nullable, where
**null means NOT MEASURED and must never be read as a measured zero** — `flags` (list of
human-readable cautions), `passed` (computed: e.g. `pbo < 0.5 and deflated_sharpe > 0`). The
report is the MVP deliverable rendered by the frontend (Phase 5).

Both diagnostics are also recorded per `Trial` (`walk_forward_oos_sharpe` /
`purged_cv_oos_sharpe`) so they reach the research pool, and summarized for gate passers by
`scripts/pool_report.py` — which prints them next to `data/null_calibration/` so the
"passers vs null" comparison is two commands, not a fresh script every session.

**Neither gates anything.** Both are diagnostics with an explicit, measurable trigger for
revisiting, recorded in their ADRs. Do not add a floor without arguing it from the null
distribution (charter §4).

Parameter stability and regime analysis (`parameter_stability.py`, `regime_analysis.py`) are
secondary and added after the core four are solid.

---

## 6. Rank information coefficient (cross-sectional only)

`app/research/cross_sectional/ic.py`. ADR-035. Per-date Spearman correlation between the signal
cross-section at *t* and each asset's return from *t* to *t+1* — the same causality
`portfolio_returns` uses (rank on t, realize t+1). `summarize_ic` returns mean, std, IR (mean/std),
t-stat (IR·√periods), hit rate and period count.

- Answers the one question a dollar-neutral Sharpe cannot: **did the ranking carry information, or
  did two names carry the P&L?** At a 0.2 quantile over ~50 names each leg is ~10 positions.
- Dates with <2 ranked names, or zero dispersion on either side, are **dropped, not scored 0** —
  "not measurable" is a different observation from "no information", and zeroing biases the mean
  toward the null.
- **Diagnostic, not a gate.** An IC floor would change what graduates; per the charter that needs
  argued methodology with evidence, and no IC distribution exists yet. Trigger to revisit: ≥50
  cross-sectional trials with an IC, then compare gate-passing vs gate-failing distributions.
- The t-stat assumes independent periods, so it is **optimistic** for a slow signal whose IC series
  is autocorrelated. Newey-West adjustment is a noted, unbuilt follow-up.

---

## 7. Gate calibration — Type-I error, power, and the detectable-edge frontier

The three sections above describe statistics. This one describes what has been measured about the
**gate as a whole**, which is what any claim made with it actually rests on. Re-run every part of it
after any `GateConfig` change; each is token-free cloud compute.

### 7.1 Type-I error (ADR-036/037) — `app/research/lab/calibration.py`
`calibrate_gate` runs the UNMODIFIED search + gate over symbols with no edge by construction:
`iid_normal_null` (textbook) and `bootstrap_null` (resamples a real symbol's bars, preserving fat
tails and vol, destroying serial structure). `null-calibration.yml` shards it and commits
`data/null_calibration/*.json`.

- Measured at N = 200 per mode: **1.0% false-graduation rate on both nulls**, **0 false graduates
  clear the ADR-018 bar**, **max DSR +0.92**.
- A shard cannot report a final answer — the deflation bar grows with the TOTAL symbols searched,
  so `merge_calibrations` re-judges every false graduate at the combined N, and refuses to merge
  across gate config versions or null modes.
- Null experiments are NEVER written to the research pool: they would inflate the MinTRL
  denominator for real hypotheses.
- Calibration identity includes the resolved grids AND a trial-accounting-method version
  (ADR-044/046). The same hypotheses priced by a different DSR denominator are a different measured
  procedure and must not reuse an old Type-I/power artifact.
- Calibration runs production's adaptive winner-family refinement by default (`refine=True`, span
  0.25) and records those inputs in both the artifact and search identity (ADR-047). Runs before
  ADR-047 were coarse-only and do not measure the selector daily discovery deploys.

### 7.2 Power (ADR-041/042) — the Type-II half
`measure_power` plants an edge of MEASURED (never derived) strength and counts detections in two
tiers: graduated, and cleared the ADR-018 bar.

- `autocorrelated_edge(phi)` — AR(1) on returns. phi < 0 is lag-1 mean reversion, phi > 0 trend.
  Measured at N = 50 per phi: **64% at oracle Sharpe 3.9, 54% at 2.6, 0% at 1.3**, both directions.
- `mean_reverting_edge(half_life, deviation_share)` — a random-walk level plus an AR(1) deviation,
  i.e. band reversion at a stated horizon. Parameterized by the deviation's SHARE of return
  variance so realized volatility is constant across horizons; otherwise a horizon sweep moves the
  volatility and the effect size with it. Measured: **0% at a 1-bar half-life, 42% at 5 bars**, at
  a held-constant oracle ≈ 2.7 — so the catalog's blind spot is FAST reversion, not reversion.
- Both processes are stationary and always-on, so every power number is an **upper bound** on power
  against real, intermittent edges.
- Effect size is bounded by the horizon: only `(1-rho)/2` of a deviation's variance is predictable
  one bar ahead, so slow band reversion cannot reach a large oracle Sharpe at equity volatility.
  Read half-lives ≥ 10 as a statement about that ceiling, not about the catalog.

### 7.3 The detectable-edge frontier (ADR-043) — `app/research/lab/frontier.py`
Power measures statistics × capture together. The frontier is the statistics alone:
`SR_true = bar(N, T) + z_p · SE(SR_true)`, with `SE = sqrt((1 + SR²/504)/T)` (Lo 2002, annualized),
solved by fixed point. At `SR = 0` that SE is exactly the `sqrt(1/T)` in
`expected_max_sharpe_under_null` — if the two ever diverge, one of them is wrong.

- Current design (607 symbols, 4.3-year holdout): a **true annualized Sharpe of 2.13** is needed to
  clear the bar 80% of the time. Printed by `scripts/pool_report.py` and by the dashboard's
  `DeflationHeadline`, computed at report time and never stored.
- Design asymmetry, and the reason a session should not "fix" the funnel by trimming the universe:
  the bar moves as `sqrt(2 ln N)` in hypotheses but `1/sqrt(T)` in holdout length — **halving the
  universe buys ~4%, doubling the holdout ~29%.**
- None of this licenses moving a threshold. A frontier the universe cannot reach is a finding to
  state plainly, not a reason to lower the bar (charter §4).

### 7.4 Capture efficiency (ADR-045) — recorded by `measure_power`
Every power run keeps the max-DSR finalist's in-sample Sharpe for every successfully SEARCHED
symbol, including non-detections. `PowerCalibration.capture_ratio` is median finalist Sharpe /
median oracle Sharpe. It returns null for legacy or partial artifacts rather than silently changing
the denominator.

- This is an **upper bound**, not holdout capture: the finalist is selected in-sample from a grid,
  so selection works in its favour. Low capture is therefore conclusive; high capture is not.
- Measured upper bounds: **0.18–0.29 at a 1-bar band-reversion half-life, 0.45–0.50 at 5 bars**.
  The grid searches 2-bar configurations at both horizons and they win at neither. Fast reversion
  is a smaller, noisier state-estimation target at held-constant oracle Sharpe, not a missing-window
  problem (ADR-045's correction to ADR-042).
- Capture ≈ 0.47 against the frontier's required true Sharpe 2.13 implies an underlying oracle
  Sharpe around **4.5** before the current pipeline is likely to find an edge. Because capture is an
  upper bound, the real requirement is worse. This is a diagnosis, never permission to lower a bar.
