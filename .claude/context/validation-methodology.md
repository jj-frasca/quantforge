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

## 3. Walk-forward splits

`app/validation/walk_forward.py`. Expanding window: train on [0, k), test on the next block,
step forward. Returns `list[(train_idx, test_idx)]`.

- **Invariant**: `max(train_idx) < min(test_idx)` for every split — never uses future data.

---

## 4. Purged K-Fold CV

`app/validation/purged_cv.py`. López de Prado (2018) ch. 7. K folds; for each test fold, **purge**
training indices within `embargo` of the test fold (overlapping labels leak), and apply the
embargo after the test block.

- **Invariant**: no training index lies within `embargo` of any test index (no leakage).

---

## 5. ValidationReport

`app/validation/report.py` — Pydantic model aggregating the above for one strategy:
`strategy_name`, `observed_sharpe`, `deflated_sharpe`, `pbo`, `n_walk_forward_splits`,
`n_purged_folds`, `flags` (list of human-readable cautions), `passed` (computed: e.g.
`pbo < 0.5 and deflated_sharpe > 0`). The report is the MVP deliverable rendered by the
frontend (Phase 5).

Parameter stability and regime analysis (`parameter_stability.py`, `regime_analysis.py`) are
secondary and added after the core four are solid.
