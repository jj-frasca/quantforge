# ADR-039: Score the purged folds, and size the embargo from the strategy's own lookback

- **Status**: Accepted
- **Date**: 2026-08-19
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Extends**: ADR-008 (validation suite), ADR-038 (walk-forward evaluation)

## Context
ADR-038 fixed one of two decorative counts on `ValidationReport` and explicitly left the other:

```python
n_purged_folds=len(purged_kfold_splits(n_obs, self._purged_folds, self._embargo)),
```

`purged_kfold_splits` is correct — contiguous test folds, training indices within `embargo` of the
test block removed, every index tested exactly once (López de Prado 2018, ch. 7). It is also
consumed by nothing. This ADR is the decision ADR-038 said purged CV deserved on its own.

Two questions have to be answered together, because the second one determines whether the first is
worth anything.

**1. What does scoring a purged fold tell us that PBO does not?** PBO already resamples: CSCV
splits the observation matrix into `n_splits` contiguous groups and evaluates every balanced
in-sample/out-of-sample combination. But CSCV **does not purge**. Its groups are adjacent, so a
strategy whose signal at bar *t* depends on a 200-bar trailing window has, at every group boundary,
test bars whose signal was computed from training bars. That is leakage across the split, and it
biases PBO toward looking *better* than the truth. It is also a different statistic: PBO reports a
*probability of rank inversion* (does the in-sample best fall below the out-of-sample median?),
never a *level*. Neither number tells you what the strategy actually earned out of sample with the
boundary leakage removed.

**2. Is the embargo big enough to remove that leakage?** `ValidationEngine`'s default is
`embargo=2`. The catalog contains strategies with lookbacks of 50, 100 and 200 bars. A 2-bar
embargo around a fold whose signal is built from a 200-bar rolling window purges roughly 1% of the
contaminated region. **A purged CV with a 2-bar embargo on a 200-bar strategy is purged in name
only** — and it would be worse than useless to report its output as a leakage-controlled number.
This is the sharper of the two findings, and it applies to the existing `n_purged_folds` count as
much as to anything new.

## Decision
**Evaluate the purged folds, and derive the embargo from the longest lookback in the config grid
rather than a fixed constant.**

### Fold evaluation
`purged_cv_evaluate(performance, splits) -> PurgedCVResult`, mirroring ADR-038's shape: for each
fold, select the config with the highest Sharpe on the **purged training rows** and score it on the
test block. Reports per-fold `selected_config` / `oos_sharpe` / `n_train` / `n_test`, plus
`mean_oos_sharpe`, `oos_sharpe_std` (the dispersion across folds), `consistency`, `n_folds` and the
`embargo` actually used. Sharpes are annualized, matching `metrics.sharpe_ratio` and ADR-038.

**What this is NOT, stated plainly because the distinction is the whole point of reporting both:**
purged CV is **not** a live-simulation estimate. A fold's training set includes rows from *after*
its test block, so the selection sees the future. That is deliberate and it is what the technique
is for — it buys many leakage-controlled resampled paths, which is how you estimate the *dispersion*
of an edge across regimes. ADR-038's walk-forward is the causal one; it answers "what would this
procedure have earned". Purged CV answers "how stable is this edge, once boundary leakage is
removed". Reporting them side by side, correctly labelled, is more informative than either alone —
and a large gap between them is itself diagnostic.

### Embargo sizing
`lookback_embargo(configs, floor)` returns the largest integer parameter across the config grid,
floored at the engine's existing default. `ValidationEngine.validate` uses it instead of the fixed
`self._embargo`, which becomes the floor.

The largest integer parameter is a **proxy** for the longest window, not a guarantee of one — it is
flagged as such in the docstring per CLAUDE.md rule 6. It is right for every catalog strategy today
(`slow`, `window`, `period`, `lookback` are the large integers; thresholds and standard-deviation
multipliers are small floats), and a proxy that is right by construction on the current catalog and
conservative when wrong is better than a constant that is wrong for two thirds of it. A strategy
whose true lookback exceeds its largest parameter would be under-purged; the fix then is to state
the lookback on the catalog entry, which is a bigger change than this ADR needs.

### Measured, 2026-08-19 (run 32297042398, N = 200 per mode, annualized)

| null mode | purged-CV median | p95 | max | walk-forward median (ADR-038) |
|---|---|---|---|---|
| `iid_normal` | +0.260 | +0.879 | +1.247 | +0.152 |
| `bootstrap:SPY` | +0.387 | +1.062 | +1.448 | +0.334 |

**Purged CV scores systematically higher than walk-forward under both nulls.** That is this ADR's
optimistic bias, measured rather than asserted: a fold's training rows include data from after the
fold, so its selection sees the future and the resulting level is flattering. The gap is the
concrete reason the two must be read side by side and never averaged. A candidate floor for either
statistic is the bootstrap p95, ≈ **+1.05** — not zero.

### Still a diagnostic, not a gate
Same reasoning as ADR-038 §"Why not a gate — yet", and the same trigger: no experiment has ever
carried the number, so no threshold can be argued from evidence. `ValidationReport.purged_cv` is
nullable and defaulted, and the null-calibration run (ADR-036/037) will measure its distribution
under a known-zero edge for free, because it runs the unmodified search.

## Alternatives considered

1. **Leave purged CV as a count, and drop the claim.** Cheapest and honest. Rejected because the
   embargo finding — that the current default is two orders of magnitude too small for the
   longest-window strategies in the catalog — is worth surfacing regardless, and it is only
   visible if something consumes the folds.
2. **Add purging to PBO's CSCV instead.** Tempting: it fixes the leakage in a number the gate
   actually uses. Rejected *for now* because PBO's `pbo_max = 0.5` is a live gate threshold
   calibrated against the current (unpurged) statistic, and changing what PBO measures changes what
   graduates — a threshold change by the back door, which charter §4 forbids without evidence. The
   right sequence is to measure the purged version alongside first. This ADR makes that possible;
   an ADR-040 can argue the swap once the two are comparable on real experiments.
3. **Full CPCV (combinatorial purged CV, many test groups per path).** The complete López de Prado
   treatment, and it produces a genuine distribution of backtest paths. Rejected on cost: it is
   `C(n, k)` fold combinations per strategy inside a search that already costs ~7 s per symbol
   across the catalog, on a discovery loop that sweeps ~600 symbols daily. K-fold is the tractable
   first step and shares all its machinery.
4. **A fixed larger embargo (e.g. 250 bars).** Simple, but wrong in both directions: needlessly
   destructive for a 5-bar strategy and still arbitrary for a 200-bar one.

## Consequences
- `ValidationReport` gains one nullable field; older pooled experiments deserialize unchanged.
- The embargo now varies per strategy, so `n_purged_folds` may change for long-lookback strategies
  — the fold *count* is unaffected (it depends only on `n_obs` and `n_splits`), only which training
  rows are purged. No existing number moves.
- Nothing that graduates today changes. This ADR adds a measurement, not a verdict.

## Reversal
Delete `purged_cv_evaluate` / `PurgedCVResult` / `lookback_embargo` from
`app/validation/purged_cv.py`, drop the `purged_cv` field from `ValidationReport`, and restore the
fixed `self._embargo` in `ValidationEngine.validate`. Nothing gates on any of it and the stored
schema is nullable, so graduation semantics are identical with or without this change.
