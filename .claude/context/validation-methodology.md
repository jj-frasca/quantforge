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
