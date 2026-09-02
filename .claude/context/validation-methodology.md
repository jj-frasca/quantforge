# Validation Methodology (Cold Memory)

Formal specs for the validation engine (Phase 4) — the layer that makes QuantForge credible.
Read when working on `backend/app/validation/`. Citations + summaries in research-papers.md.
Each component encodes a mathematical invariant as a Hypothesis property test.

---

## 1. Deflated Sharpe Ratio (DSR) — value form

`app/validation/deflated_sharpe.py`. Adapted from Bailey & López de Prado (2014).

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

**Important source distinction (FINDING-007, resolved by ADR-054).** The paper's DSR is a
probability-form PSR against the expected-max threshold and includes sample length, skewness, and
kurtosis. QuantForge's stored `deflated_sharpe` field is a selection-adjusted Sharpe **margin**, not
that probability, and its `> 0` gate asks whether observed Sharpe clears the multiplicity threshold.
**Never call the margin the Deflated Sharpe Ratio.** Both statistics now exist:

- `probabilistic_sharpe_ratio(observed_sr, benchmark_sr, n_returns, skew, kurtosis)` — Eq. 1, with
  **RAW** kurtosis (a Normal series is 3.0, which reduces the denominator to `1/sqrt(n-1)`). pandas
  reports EXCESS kurtosis; `return_moments()` in `backtesting/metrics.py` does the conversion and is
  the only thing that should be feeding this function.
- `deflated_sharpe_probability(...)` — the paper's Eq. 2: PSR against `expected_max_sharpe`.
- `Trial.deflated_sharpe_probability` records it on every new search, nullable so the ~3,200
  pre-ADR-054 pool rows read as *not measured* rather than as a probability of zero.

**The scale trap, which is why this took two attempts.** Everything on a `Trial` is ANNUALIZED; the
PSR is a function of the PER-PERIOD Sharpe and the per-period moments TOGETHER. Mixing one
annualized input with two per-period ones silently rescales the probability instead of failing.
`whole_search_deflated_sharpe_probabilities()` divides the observed Sharpe AND the trial dispersion
by the same `sqrt(252)`; do not add a caller that skips one of them.

**The gate still gates on the MARGIN.** `PoolReport.statistic_agreement` counts how often the two
statistics reach the same verdict on the same finalist, at a stated `probability_reference` that
nothing gates on. Switching the gate to the probability is a threshold change: it requires a fresh
Type-I error and a fresh power curve for the new statistic, all three calibration workflows
re-dispatched together at the same `n_bars` (§7.2), and its own ADR.

**Search-level accounting (ADR-046/050).** A StrategyLab run first evaluates parameter configs inside
families and then selects across the family finalists. DSR must price that whole selection, not
reset inside each family. Both longitudinal and cross-sectional search pool every current candidate
Sharpe to estimate one Normal-consistent IQR scale for `sr_std`, use cumulative concrete-config
`lifetime_trials` for N, and apply the same haircut to every family finalist before the overall
argmax. The robust central scale prevents a minority of real signal-loading strategies from raising
their own supposed-null haircut without bound (ADR-050); fewer than four candidates retain sample
standard deviation. `Trial` is therefore a compact family-finalist summary with
`n_evaluated_configs`; the number of stored summaries is NOT the margin or MinTRL denominator.
Historical longitudinal pool counters predate this field and remain a lower bound; generated
records are never guessed/backfilled against today's catalog.

**Pool reporting (ADR-066).** `Experiment.lifetime_trials` is already cumulative per symbol. The
programme-wide trial headline therefore sums the maximum counter once per symbol; summing every
retained experiment would count the same prior trials repeatedly. The aggregate is the sum of the
per-symbol DSR/MinTRL denominators, not one global denominator.

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

**ADR-078: it carries a drift control, exactly as walk-forward does.** `purged_cv_evaluate` takes
an optional `benchmark` of per-bar returns and reports `mean_oos_hold_sharpe` — buy-and-hold scored
on the same folds, averaged over the folds that were KEPT (a fold purged away entirely is dropped,
and a benchmark averaged over blocks the strategy was never scored on is not the paired quantity).
`ValidationEngine` passes the same series it passes to walk-forward, `run_search` stores it as
`Experiment.purged_cv_hold_sharpe`, `calibrate_gate` collects
`NullCalibration.purged_cv_hold_sharpes`, and `compare_with_null` emits a `purged-CV excess` row
beside the raw one.

**The two hold Sharpes are NOT interchangeable.** Purged CV tests every index exactly once, so its
control covers the whole searched window; walk-forward's test blocks skip the first train block, so
its control covers a suffix. Substituting one for the other mixes a correction measured on one
index set into a statistic measured on another — which is the confound both exist to remove.

ADR-068 had deferred this on the grounds that "purged CV's folds are not a prefix-ordered benchmark
window". ADR-078 overturned it: fold ordering is a fact about SELECTION, and buy-and-hold has no
config to select. The 7,400-bar nulls and the first 88-symbol matched real cohort now carry the
control (FINDING-017). Real paired excess is `-0.000`; its difference from the bootstrap null is
`+0.000 [-0.048, +0.002]` and from iid-normal is `+0.000 [-0.048, +0.000]`, clustered by symbol.
Both intervals span zero. The retained 5,400-bar nulls remain legacy and correctly unmeasured.

**ADR-080 applies to both controls.** Walk-forward and purged-CV OOS/hold values share one
per-symbol calibration record, remain independently nullable, and are paired only within that
record. Shard merge rejects mixed legacy/paired generations and duplicate symbols. This changes no
raw distribution or gate; it prevents complementary missingness from becoming cross-symbol excess.

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

- Current published result — run 32354284731 (2026-08-20), ADR-046/047/048 accounting **with
  ADR-050's IQR dispersion**, judged at the hunt's own **5400-bar** history (ADR-051), N = 200 per
  mode: **0 false graduates on both nulls**, **0 clear the ADR-018 bar**, max DSR **-0.415 iid /
  -0.269 bootstrap**. The prior 1.0% / max +0.92 result belongs to the coarse-only, uncapped
  accounting procedure.
- Current 7,400-bar result — run 33287465013 (2026-08-30), N = 200 per mode: **0 false graduates on
  both nulls**, **0 clear the bar**, max DSR **-0.368 iid / -0.253 bootstrap**, `deflation_bar`
  1.343. Carries ADR-068's paired hold distribution; the 5,400-bar pair never will.
- **Only the iid-normal null is bit-reproducible across days; the bootstrap null is not, by
  construction.** Re-running the identical dispatch on 2026-08-30 reproduced iid's max DSR to the
  digit (−0.368) while bootstrap's moved −0.261 → −0.253. `_source_frame` fetches SPY up to *now*,
  so the resampled marginal changes every time the real series gains a bar. That is not drift in the
  gate and not a defect: it is the null tracking the symbol it is built from. Quote a bootstrap
  number with its run id, and never treat a small move in it as a change in the pipeline.
- **Every calibration is judged at the hunt's history length, not a round number (ADR-051).** The
  drivers previously planted 3000 bars while `scripts/shard_hunt.py` starts at 2005-01-01 and real
  names carry ~5400. `n_bars` is now a `--n-bars` driver flag, a workflow input, and a recorded
  field on both `NullCalibration` and `PowerCalibration`; an empty list means an artifact predating
  the field, never a run that saw no bars.
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
- Production enforces `GateConfig.trial_budget` across coarse and refined candidates (ADR-048).
  Families are canonicalized, receive a two-config PBO minimum, and share remaining capacity by
  fair water-filling; oversized grids use deterministic maximin parameter-space coverage. The
  refinement pass is one family-sized bucket inside the same cap. Calibration identity hashes the
  budgeted grids, refinement reserve, and allocation-method version. Pre-ADR-048 artifacts measure
  the uncapped 667-config coarse family and are stale for production.

### 7.2 Power (ADR-041/042) — the Type-II half
`measure_power` plants an edge of MEASURED (never derived) strength and counts detections in two
tiers: graduated, and cleared the ADR-018 bar.

- `autocorrelated_edge(phi)` — AR(1) on returns. phi < 0 is lag-1 mean reversion, phi > 0 trend.
  **Current published curve** (run 32355803804, production parity at the hunt's 5400-bar history):
  **64% at oracle 3.90 (32/50 clear the ADR-018 bar), 34% at oracle 3.97 reverting (17/50), 14%/22%
  at oracle ≈ 2.6, 0% at oracle ≈ 1.3.** The intermediate 0/50-everywhere result was measured on
  3000 bars and is superseded (ADR-051) — do not requote it.
- `mean_reverting_edge(half_life, deviation_share)` — a random-walk level plus an AR(1) deviation,
  i.e. band reversion at a stated horizon. Parameterized by the deviation's SHARE of return
  variance so realized volatility is constant across horizons; otherwise a horizon sweep moves the
  volatility and the effect size with it. Run 32355806443 measures **0/50 at every horizon** at
  oracle ≈ 2.6 with **DSR passing 0/50 in every cell**, while AR(1) reversion at the SAME oracle is
  detected 22% with DSR passing 39/50. The difference is capture — **20.7% / 21.8% / 24.6% / 37.2%
  at half-lives 1 / 2 / 3 / 5** against 55.1% for AR(1) — so this is what the catalog can express,
  not what the statistics permit. ADR-042's "the asymmetry was the horizon, not the family" reading
  describes the pre-ADR-046/047/048 procedure at 3000 bars and does NOT describe production: at
  full history the horizon does not rescue band reversion.
- Both processes are stationary and always-on, so every power number is an **upper bound** on power
  against real, intermittent edges.
- ADR-049 records per-component pass counts (`dsr`, `pbo`, `stability`, `mintrl`, `holdout`,
  `beats_buy_and_hold`) because a composite zero cannot identify its own mechanism. Empty counts on
  a legacy artifact mean attribution was not preserved, never that every component had zero passes.
- Diagnostic runs 32341906980/32341908789 found **DSR 0/50 in all 12 cells**. At phi +0.30,
  PBO passed 43/50, stability 40/50, and MinTRL/holdout/beat-buy-and-hold 50/50. FINDING-006 isolates
  the cause: whole-search DSR estimates null dispersion from the current candidates, so the planted
  signal widened `sr_std` from 0.510 (matched iid seed) to 1.703 and raised the haircut from 1.410
  to 4.698 against observed Sharpe 2.937. Do not lower `dsr_min`; a null-consistent dispersion
  decision requires its own ADR and full recalibration.
- ADR-050 replaces whole-search sample standard deviation with a Normal-consistent IQR scale. Its
  refresh has now landed on all three workflows (Type-I 32354284731, power 32355803804/32355806443)
  and the numbers above are that refresh. **Any further change to the estimator, the catalog, or
  the grids invalidates all three again — re-dispatch them together, at the same `n_bars`.**
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
- **ADR-063 acts on that asymmetry rather than restating it.** The search window was
  `datetime(2005, 1, 1)` copied into nine drivers, so `T` was a constant, not a property of the
  data — Yahoo serves 1990 for 74% of the discovery universe. `app/research/lab/history.py` now
  holds `SEARCH_HISTORY_START` (1990-01-01, the single-name search and the calibrations that mirror
  it), `RECENT_HISTORY_START` (2005-01-01, the paper book and anything needing only a recent tail)
  and `CALIBRATION_N_BARS`. Sampled median history goes 5,448 → **7,444 bars**, holdout 4.3y →
  **5.9y**, and the required true Sharpe 2.13 → **1.82** (1.63 for the 25% of names with full
  1990 history). No threshold moves: the ADR-018 bar and MinTRL are derived from `(N, T)` per symbol
  at judgement time, and the estimate's standard error falls with the bar. **Any calibration
  artifact at `n_bars=5400` describes a gate that no longer runs** — re-dispatch all three before
  quoting a Type-I error or a power number.

- **ADR-063 MEASURED (2026-08-29, `n_bars=7400`).** Type-I error unchanged: **0/200 on both nulls**,
  max DSR −0.261 / −0.368, `deflation_bar` **1.343** (was 1.722). AR(1) detection
  **34/22/0/0/14/64% → 40/36/0/0/24/66%** for φ = −0.3…+0.3 — four of four cells that had an edge to
  find rose, none fell, on a deterministic sweep. **The ADR's own criterion FAILED**: the cells it
  named (φ = ±0.1, band half-lives 3–5) are still 0%, because it could not distinguish "0% for want
  of power" from "0% because ADR-061 showed nothing is recoverable there". Phrase the next such
  criterion over the cells where the achievable oracle exceeds the requirement.
- **Capture FELL and that is a correction, not a regression.** Band net capture
  32/29/31/45/56/58% → **31/30/30/42/51/50%**; against the achievable oracle 105/103/104% →
  **97/98/88%** at half-lives 5/10/20. ADR-045's numerator is an in-sample maximum over the searched
  grid, so 1,600 more in-sample bars regress it toward the value it estimates. **The earlier, higher
  ratios carried more selection bias — quote the new ones.**

### 7.4 Capture efficiency (ADR-045) — recorded by `measure_power`
Every power run keeps the max-DSR finalist's in-sample Sharpe for every successfully SEARCHED
symbol, including non-detections. `PowerCalibration.capture_ratio` is median finalist Sharpe /
median oracle Sharpe. It returns null for legacy or partial artifacts rather than silently changing
the denominator.

- This is an **upper bound**, not holdout capture: the finalist is selected in-sample from a grid,
  so selection works in its favour. Low capture is therefore conclusive; high capture is not.
- The grid searches 2-bar configurations at both horizons and they win at neither. Fast reversion
  is a smaller, noisier state-estimation target at held-constant oracle Sharpe, not a missing-window
  problem (ADR-045's correction to ADR-042).
- Capture ≈ 0.47 against the frontier's required true Sharpe 2.13 implies an underlying oracle
  Sharpe around **4.5** before the current pipeline is likely to find an edge. Because capture is an
  upper bound, the real requirement is worse. This is a diagnosis, never permission to lower a bar.

**ADR-055: take the ratio against the NET oracle.** `oracle_sharpes` is cost-free; every finalist in
the numerator was charged 10bp on turnover by `BacktestEngine`, and the oracle is a *sign* strategy
turning over up to 1.19 per bar. `net_oracle_sharpes` charges it the same rate, and
`net_capture_ratio` is the comparable ratio. Both are pydantic computed fields, so they are served
rather than re-derived by each reader — do not reimplement the division in a script or a component.

| planted (2026-08-20, 5400 bars) | oracle | net oracle | detected | capture | net capture |
|---|---|---|---|---|---|
| AR(1) φ = +0.30 / −0.30 | +3.90 / +3.97 | +2.83 / +2.42 | 64% / 34% | 76% / 70% | 105% / 114% |
| AR(1) φ = +0.20 / −0.20 | +2.54 / +2.63 | +1.38 / +1.15 | 14% / 22% | 64% / 55% | 118% / 126% |
| AR(1) φ = ±0.10 | +1.25 / +1.33 | **+0.02 / −0.09** | 0% | 50% / 40% | *refused* |
| band, half-life 1 / 3 / 5 | +2.60 / +2.70 / +2.65 | +1.70 / +2.13 / +2.21 | 0% | 21% / 25% / 37% | **32% / 31% / 45%** |
| band, half-life 10 / 20 | +2.03 / +1.45 | +1.71 / +1.24 | 0% | 47% / 50% | 56% / 58% |

Three rules follow. (1) **Never quote "0% power at oracle 1.3"** — net of costs that cell held no
achievable edge, and the ratio is refused when the net oracle sits inside Lo (2002)'s Sharpe
standard error at the cell's own history length. (2) **Net capture above 100% is expected, not a
bug**: the numerator is selected in-sample from a grid while the denominator is a fixed sign rule
that pays to flip. It is the clearest demonstration that this ratio is an upper bound. (3) ~~**The
band gap is the standing finding** — what the catalog cannot express is fast reversion to a
slow-moving level.~~ **RETIRED by ADR-061 (2026-08-20). Do not restate it in any form.** That
reading divided by an oracle computed from the process's LATENT deviation, which no causal strategy
can see. See §7.6.

**ADR-057/058: rule 3 above is now SHARPER — the fast-half-life gap is a RECOGNITION failure.**
`PowerCalibration.finalist_strategy_names` records which strategy won each searched symbol, so a
cell's finalists can be grouped by catalog category. On band reversion (5400 bars, 34-strategy
catalog + one probe strategy, superseded artifacts `2eede83f…`):

| band half-life | 1 | 2 | 3 | 5 | 10 | 20 |
|---|---|---|---|---|---|---|
| finalists from **Mean Reversion** | 18% | 44% | 64% | 94% | 94% | 82% |
| net capture | 32% | 30% | 31% | 45% | 56% | 58% |

At half-life 1 the max-DSR search selects a **Trend** strategy 68% of the time on a process that is
by construction fast reversion. Capture tracks the recognition share. The AR(1) control from the
same dispatch recognizes perfectly (100% Mean Reversion finalists at φ = −0.2/−0.3; 66–74% Trend at
φ = +0.2/+0.3; a scattered mix only in the |φ| = 0.1 cells that hold no achievable edge).

**ADR-059: the headline capture at fast half-lives is not the MATCHED capture.** Each cell now
records the best in-sample Sharpe per catalog category and serves `net_capture_by_category` under
the same ADR-055 refusal. Measured on the 34-strategy catalog at 5400 bars:

| band half-life | 1 | 2 | 3 | 5 | 10 | 20 |
|---|---|---|---|---|---|---|
| headline net capture | 32% | 29% | 31% | 45% | 56% | 58% |
| **Mean Reversion (the matched row)** | **22%** | 26% | 29% | 44% | 56% | 58% |
| Trend | 31% | 25% | 21% | 20% | 26% | 35% |

At half-life 1 the headline is carried by Trend — strategies fitting the random-walk level, 83% of
return variance there — while everything aimed at the planted reversion keeps 22%. **Quote 22%, not
32%, for what the catalog's reverting strategies keep of a fast planted reversion.** The AR(1) sweep
self-checks the taxonomy: Mean Reversion is the maximum row at φ = −0.3/−0.2 (114%/126%) and Trend
or Breakout at φ = +0.2/+0.3 (116%/103%, Mean Reversion 14%/5%).

**These sweeps are deterministic** — fixed seeds, no RNG in the search — so two runs of the same
catalog agree to the symbol, and a difference between two catalogs is a real effect on that sample
rather than sampling noise. Generalizing its MAGNITUDE to the population still carries ±6.6pp at
n = 50.

**Consequences for anyone tempted to close the gap with a new strategy.** ADR-056 added exactly the
strategy the old reading called for — one that estimates a slow level and a fast deviation on
independent timescales — and net capture moved ≤ +0.7pp in every cell while the new strategy won
1–5 of 50 searches. ADR-058 removed it. **At half-lives 1–3 no reverting strategy wins the in-sample
comparison, so the selection step never gets as far as asking which reverting strategy is best.**
Judge the next attempt against the finalist CATEGORY MIX at half-lives 1–3, not against capture
alone; and use `compare_power_sweeps(before, after)`, which refuses to call a capture delta
attributable unless the finalist mix moved with it (a larger grid raises an in-sample maximum on its
own).

### 7.6 The achievable oracle (ADR-061) — the band gap was the benchmark

`mean_reverting_edge` plants `log price = random-walk level + AR(1) deviation` and only the SUM is
observable, so the oracle every band capture ratio was divided by knows a state no strategy can see.
`filtered_deviation` runs the two-state Kalman recursion **with the true process parameters** — an
upper bound on any causal price-based strategy — and `achievable_capture_ratio` divides by that,
under the same refusal ADR-055 applies to the net ratio. Measured, 50 symbols per cell at 5400 bars:

| band half-life | 1 | 2 | 3 | 5 | 10 | 20 |
|---|---|---|---|---|---|---|
| latent-state oracle, net | +1.70 | +1.93 | +2.13 | +2.21 | +1.71 | +1.24 |
| **achievable (Kalman) oracle, net** | **−0.08** | **+0.22** | **+0.51** | **+0.95** | **+0.93** | **+0.70** |
| capture vs latent (the headline) | 32% | 29% | 31% | 45% | 56% | 58% |
| **capture vs achievable** | *refused* | 261% | 130% | 105% | 103% | 104% |

**What to say about band reversion from now on.** The catalog converts essentially all of the
recoverable edge from half-life 3 onward; at half-lives 1–2 there is nothing recoverable to convert
(the optimal filter with perfect parameter knowledge nets −0.08 at half-life 1). The 0/50 detection
in every band cell is then fully explained by ADR-043's frontier — an achievable net Sharpe of at
most ≈0.95 against a ≈2.1 requirement — **without any reference to the catalog at all. A gate that
graduated one of these cells would be wrong.**

Two things this closes, so they are not retried:
- **A better estimator cannot help.** At the production deviation shares the Kalman filter and a
  naive EWM residual correlate with the true deviation equally (0.270 vs 0.271 at half-life 1). The
  estimation problem binds, not the estimator. ADR-056's strategy WAS the naive estimator and the
  per-symbol Kalman gain it proposed as a follow-up is the optimal one.
- **A different selection rule cannot help.** Matched-family pick rate at half-life 1 is 0% under
  max-DSR (production), 0% under max in-sample Sharpe, 10% under max walk-forward OOS and 0% under
  max purged-CV OOS. Every criterion agrees because the reverting families genuinely score lower on
  all of them.

The AR(1) sweep deliberately records no achievable oracle: its state IS the observed return, which
is why its capture already exceeds 100%.

**ADR-069/070/071: selection-rule sweeps must preserve the selected finalist.** ADR-069 measured
`observed` against `walk_forward` cross-family selection; the non-default arm failed its pre-stated
power criterion, so ADR-070 keeps `observed` as production default. FINDING-010 then found that
calibration extracted diagnostics and attribution from max DSR even when `run_search` sent the
walk-forward winner to the holdout and gate. ADR-071 makes every finalist-level artifact field use
the requested selection rule. ADR-070's detection/Type-I counts remain valid because they came from
the correctly selected gate result; its observation about the non-default null diagnostic is not
reusable without a corrected rerun. Non-default artifacts were never committed.

**ADR-079: persist the real finalist, too.** FINDING-015 found that pool reporting still rebuilt
every real finalist as max DSR. `best_strategy_name` cannot identify a trial after refinement adds
a second trial from the same family. New experiments therefore persist `selected_trial_index`, and
all finalist-level pool statistics resolve it through one checked helper. Legacy rows retain the
historical max-DSR reading; no old non-default identity is invented.

### 7.5 The real universe against the null (ADR-051) — `scripts/pool_report.py`
ADR-038/039 recorded a walk-forward and a purged-CV OOS Sharpe on every trial with a stated revisit
trigger: read them against `data/null_calibration/*.json`. Two things had to be repaired before that
was possible, and both are the general lesson.

- **Compare the same statistic on both sides.** The pool's summary read gate passers; the null
  artifacts record the max-DSR finalist of every SEARCHED symbol. `PoolReport` now carries
  `walk_forward_finalists` / `purged_cv_finalists` alongside the gate-passer fields, and the report
  distinguishes *no experiment carries it*, *no experiment passed the gate*, and a measured median.
  This matters permanently, not once: under ADR-046's repaired denominator the 2026-08-20 discovery
  run produced **0 graduates from 603 experiments**, so the gate-passer window is empty and only
  the finalist window is readable.
- **Match the identity before quoting a difference.** Compare `search_config_version` and
  `gate_config_version` on both sides and check the bar counts. `Experiment` now records the former
  (ADR-052) precisely because establishing it once required diffing commit timestamps against
  workflow start times.

**Measured (2026-08-20, matched at fingerprint `3f36fda2…` and 5400 bars).** Real: 603 finalists.
Null: 200 per mode.

| statistic | real median | bootstrap null | iid-normal null |
|---|---|---|---|
| walk-forward OOS Sharpe | **+0.561** | +0.652 | +0.414 |
| purged-CV OOS Sharpe | **+0.597** | +0.661 | +0.475 |

Mann-Whitney one-sided for real > null: **p = 1.0000 vs bootstrap** on both statistics, **p < 0.0001
vs iid-normal** on both. Every catalog strategy trades serial structure; the bootstrap null has none
and preserves SPY's return shape exactly. So the advantage over iid-normal is **distributional, not
predictive**. Read it as a joint statement about this universe and this catalog — not as a threshold
argument (charter §4), and not as "the catalog cannot capture serial structure", which ADR-042
measured to be false at 42% detection on a planted half-life-5 reversion. Limitations are in
ADR-051 §Measured; the sharpest is that the bootstrap resamples SPY rather than each symbol.

**ADR-064 made the report state that verdict instead of refusing it.** The identity check above was
implemented as exact equality between the pool's *median* `n_bars` and the null artifact's, and a
median that grows by a bar per trading day can essentially never equal a fixed integer — so from the
moment the pool grew past 5,400 the report printed `NOT COMPARABLE -- history 5444 bars vs 5400` on
all four rows. `compare_with_null(report, calibrations, experiments)` now selects the experiments
whose `n_bars` is within `HISTORY_TOLERANCE` (10%) of THAT artifact's, summarizes the real side over
exactly those, reports `matched_n` / `matched_n_bars` on every row, and refuses below `MIN_MATCHED`
(30). The search-family test reads the same subset — refusing a comparison because of rows outside
it describes a comparison nobody made. Rows with no `n_bars` are excluded, never assumed to match.

**Measured (2026-08-29): 2,427 matched experiments at a median 5,445 bars, 100% fingerprint
`3f36fda2…`, against nulls at 5,400.**

| statistic | matched real median | bootstrap null (median / p95) | iid-normal null (median / p95) |
|---|---|---|---|
| walk-forward OOS Sharpe | **+0.542** | +0.652 / +0.983 | +0.414 / +0.796 |
| purged-CV OOS Sharpe | **+0.584** | +0.661 / +1.003 | +0.475 / +0.803 |

**Does not separate on any of the four**, and against the bootstrap the real median sits *below* the
null's. The pool-wide medians are +0.567 / +0.598 — quoting those against a 5,400-bar null is the
error this repairs, so quote the matched numbers. After ADR-063 the pool goes bimodal (5,448 legacy /
7,400+ re-searched) and the two cohorts must be read against their own nulls; `matched_n` on each row
is what tells you which cohort you are looking at.

**Provenance, and why the tree can answer again (ADR-065).** Those matched numbers were measured
against the **5,400-bar** null artifacts, which ADR-063's re-dispatch overwrote in place with the
7,400-bar run (`6efcb7e`) the same day — leaving a published measurement reproducible only from
commit `dbba1ed`. The cause was the filename: one path per null mode. Artifacts are now named for
the history they measured (`bootstrap_spy_5400.json`, `bootstrap_spy_7400.json`); the superseded
5,400-bar pair was restored from `dbba1ed` under its own name and **the table above reproduces from
the working tree**. A re-run at the same length still overwrites — that is a re-measurement of the
same pair — so the directory grows once per genuine change of history length, not once per run.

## §7.6 Excess over buy-and-hold — what the OOS statistic is actually denominated in (ADR-068)

The walk-forward OOS Sharpe carries the **drift of the series it was computed on**. Measured
2026-08-30, where "underlying" is `mean/std × √252` of the daily returns the finalist was searched
over — buy-and-hold, computed exactly as `walk_forward._sharpe` computes a strategy's:

| side | underlying | finalist walk-forward OOS median | excess |
|---|---|---|---|
| `iid_normal` null (drift 0.0003 / vol 0.012) | 0.397 | +0.414 (5,400) / +0.416 (7,400) | +0.017 / +0.019 |
| `bootstrap:SPY` null (SPY 1993-01-29→2026-08-28) | 0.650 | +0.652 (5,400) / +0.622 (7,400) | +0.002 / −0.028 |
| real matched cohort (5,445 bars) | 0.546 (39-symbol sample) | +0.542 | −0.004 |

**Then measured pairwise, per symbol** (run 33287465013 → `a61beb0`, 200 nulls per mode at 7,400
bars, 0 false graduates, 16/16 shards green). The excess here is the median of the per-symbol
DIFFERENCES, which is the statistic `compare_with_null` reports — not the difference of medians:

| null (7,400 bars) | OOS median | its own hold median | paired excess (median / mean) | excess p95 | corr(OOS, hold) | beats holding |
|---|---|---|---|---|---|---|
| `bootstrap:SPY` | +0.622 | +0.652 | **−0.006** / −0.028 | +0.096 | **0.884** | 18.5% |
| `iid_normal` | +0.416 | +0.394 | **+0.000** / +0.012 | +0.325 | 0.652 | 36.0% |

Three consequences worth carrying forward:
1. **The paired excess is zero on a null**, not merely small — so the level of the raw statistic is
   the generated series' drift and nothing else.
2. **The searched finalist usually loses to holding** on structure-free data (beats it 18.5% /
   36.0% of the time): it pays turnover for a signal that is not there, as it should.
3. **The excess band is ~10× tighter** (bootstrap p95 +0.968 raw → +0.096 excess). Under §7.5's
   verdict rule that makes the drift-controlled comparison far more sensitive — a real edge no
   longer has to out-run the spread of market drift to show up.

**Every row lands on its own underlying's buy-and-hold Sharpe to within ±0.03.** Two of them are
nulls with no exploitable structure by construction, so the level is not evidence of anything — and
§7.5's −0.11 "gap" between the pool and the bootstrap null is the gap between SPY's 33-year drift
and the median pool symbol's. Read the other way it is the cleanest statement of gate honesty here:
**what the search adds out-of-sample over holding the same series across the same windows is +0.002
to +0.019 on data with no edge, and −0.004 on real symbols.**

`walk_forward_evaluate(performance, splits, benchmark=)` scores the benchmark on the SAME test
indices with the same annualization and mean-over-splits, reporting `mean_oos_hold_sharpe`;
`ValidationEngine` passes the frame's close-to-close returns; `Experiment.walk_forward_hold_sharpe`
and `NullCalibration.walk_forward_hold_sharpes` persist it; `compare_with_null` emits a
`walk-forward excess` row per null mode beside the raw row, with §7.5's verdict rule applied to it.
Rules that hold here:
- **The raw row stays.** A published verdict is not restated on a new statistic in place.
- **Absent is not zero** (ADR-067). Every artifact written before ADR-068 carries neither side of
  the difference, so the row prints `NOT MEASURED` until the pool is re-searched and the null
  re-dispatched. An excess of zero is a measurement nobody made.
- **The two null lists are paired per searched symbol.** ADR-080 makes that identity structural:
  new calibrations store one `NullSymbolDiagnostics` record per symbol and excess is derived from
  fields on that record. Equal-length partial legacy arrays are refused; positional legacy pairing
  is allowed only when both sides contain exactly `n_symbols` entries. The original arrays remain
  raw-distribution/API projections, not pairing identity.
- **Purged-CV is a separate measurement, not a reused walk-forward control.** ADR-078 later added
  its own whole-window buy-and-hold benchmark because purged folds partition the searched window;
  neither control may stand in for the other.


## §7.7 The real side of the excess row, and the two-sided band (ADR-072)

Measured 2026-08-31, the first time both sides of the difference existed. 77 experiments over 66
symbols at 7,345 bars carry `walk_forward_hold_sharpe` and match the 7,400-bar nulls under §7.5's
±10% tolerance; both sides carry fingerprint `3f36fda2…`.

| side | n | median | mean | p5 | p25 | p75 | p95 | share < 0 |
|---|---|---|---|---|---|---|---|---|
| **real, matched cohort** | 77 | **−0.125** | −0.186 | −0.549 | −0.308 | −0.018 | +0.021 | **75.3%** |
| `bootstrap:SPY` null, 7,400 | 200 | −0.006 | −0.028 | −0.233 | −0.037 | +0.000 | +0.096 | 55.5% |
| `iid_normal` null, 7,400 | 200 | +0.000 | +0.012 | −0.251 | −0.035 | +0.057 | +0.325 | 49.5% |

**What the search adds out-of-sample, with drift removed from both sides, is −0.125 on real symbols
and ≈0 on data with no edge by construction.** The real median sits at the bootstrap null's 11.5th
percentile and the iid null's 14.0th. Quote it as a statement about the search — the in-sample
argmax fits structure that does not persist — not about the market.

`NullComparison` carries `null_p5` on every row and `real_below_null_p5` on the centered one only.
The raw rows stay one-sided on purpose: §7.6 measured that their level IS each side's own drift, so
a real median under a null says the median pool symbol drifted less than SPY. **The verdict does not
flip on today's numbers** — −0.125 is inside both nulls' p5 — and that is reported rather than
worked around.

**The open question ADR-072 recorded, and how ADR-075 closed it.** The row compares a median of 77
against a band over individual null draws — the right yardstick for "could ONE SYMBOL look like
this" (one easily could), the wrong one for "is the pool's CENTRE different from the null's", which
is what the row is asked. The naive rescaling (SE of a median of 77 ≈ 0.016 → about 7 SE) assumes 77
independent draws, and they are 66 symbols over one calendar window with `fifty_two_week_high`
winning 30 of 77.

**ADR-075: `_clustered_difference_ci` reports a 95% interval for `median(real) − median(null)`,
resampling the real side BY SYMBOL** (all of a symbol's experiments enter together) and the null
side by draw (each null symbol is an independently generated series), B = 20,000, seed 7 — the same
constants §7.8's bootstrap uses.

**FINDING-011:** ADR-064/067's `comparable` guard applies before this interval is exposed. A row
refused for search-family identity, matched history, or fewer than 30 measured diagnostics retains
its medians and mismatch as context but carries no difference interval and cannot say `EXCLUDES
ZERO`. The same 30-observation floor applies to the interval's effective symbol-cluster units, not
only to experiment rows. The dashboard repeats both guards so a stale payload cannot turn a refusal
or one-cluster resample into a finding.

| null (7,400 bars) | difference | 95% CI, symbol-clustered (66 clusters) |
|---|---|---|
| `bootstrap:SPY` | **−0.119** | **[−0.215, −0.061]** — excludes zero |
| `iid_normal` | **−0.125** | **[−0.218, −0.063]** — excludes zero |

**The project's central claim becomes: the search's drift-controlled contribution on real symbols is
distinguishable from what the same search contributes on data with no edge by construction, and it
is distinguishable in the NEGATIVE direction.** Three qualifications are part of the sentence:
- **The interval is a LOWER BOUND on its own width.** Symbol clustering removes within-symbol
  repeats and symbol-level heterogeneity, not the cross-sectional correlation of one shared calendar
  window. **FINDING-012:** one correlated 200-symbol null panel is not enough—it gives one draw of
  the panel median, and feeding its symbols to the existing elementwise bootstrap erases their
  dependence again. **ADR-081 accepts the unspent design:** equal-symbol real medians, joint iid
  resampling of complete calendar vectors, 400 independent whole-panel replicates, and a separate
  manual workflow sharded only by complete panel index. The existing result remains qualified until
  that instrument is implemented, authorized, measured, and interpreted in a later ADR. The first
  non-measuring slice is in `app/research/lab/panel_null.py`: frozen cohort/replicate identity,
  batching-invariant global-index seeds, fail-closed whole-panel consolidation and equally strict
  direct final-artifact validation. Every persisted real/panel statistic must be finite. Generation,
  inference, workflow dispatch, and the sole-writer result remain pending.
- **The single-draw verdict is unchanged and reported beside it**, per ADR-068's rule that a
  published verdict is not restated on a new statistic in place. They size different questions.
- **It was not a blind test.** ADR-075 §"Full disclosure": the point estimate was known before the
  scheme was fixed, so the pre-registration covers the procedure, not the answer.

## §7.8 Reading a change in the SEARCH WINDOW (ADR-074)

ADR-063's second clause ("the pool's median holdout Sharpe must not fall") is **unanswerable as
phrased**: a holdout Sharpe exists only on a `Graduate`, 220 of the pool's 221 graduates are
`legacy-unspecified`, and the live family has produced exactly one in 3,029 experiments. It is the
third criterion in this project stated over a quantity nobody sized first — check the sample size
of the statistic BEFORE writing the threshold.

`compare_search_windows(experiments)` reads it on the finalist instead, and the pairing rules are
the load-bearing part:
- **Within symbol.** The cross-symbol form was measured and rejected: under one family `n_bars`
  varies mostly with listing age, and the <6,000 / ≥6,000-bar cohorts share **zero symbols**.
- **Within search family**, per §7.5's identity rule.
- **Repeat runs at one window collapse to that symbol's median**, so a name the discovery happened
  to re-search five times does not outweigh one it searched once.
- **Every delta carries a bootstrap 95% interval** (20k draws, seed 7). ADR-070: a point estimate
  with no interval is what made two pre-stated criteria unreadable.

| paired delta (long − short) | n | median | 95% CI |
|---|---|---|---|
| finalist walk-forward OOS — **surrogate**, each side carries its own window's drift | 368 symbols | −0.038 | [−0.060, −0.009] |
| finalist in-sample observed | 368 symbols | +0.012 | [−0.005, +0.034] |
| **drift-controlled excess — the criterion** | 45 symbols | **−0.074** | **[−0.157, +0.030]** |

The longer window changes which strategy the search picks on **257 of 368** symbols.
`scripts/window_experiment.py N` supplies the criterion's short side by re-searching a deterministic
sample at `PRE_ADR063_SEARCH_START` (pinned in `history.py`, never a literal in a driver) and
writing to its own file — the pool is read as the ADR-062 prior only. **The interval includes zero,
so ADR-074's pre-stated criterion does not fire and ADR-063's window stays.** Two things it did
settle: removing the drift confound made the effect *larger* (−0.074 vs −0.038), so the confound is
not what produced the surrogate; and the same 45 deltas give a **mean** of −0.086 against SE 0.032,
which would have fired a criterion stated on the mean. **Pre-state the ESTIMATOR, not only the
threshold** — a bootstrap median is robust but costs ≈1.6× the sample of a mean. Rerun at n ≈ 75.
