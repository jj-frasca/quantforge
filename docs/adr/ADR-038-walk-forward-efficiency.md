# ADR-038: Walk-forward splits must judge something — measure walk-forward efficiency

- **Status**: Accepted
- **Date**: 2026-08-19
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Extends**: ADR-008 (validation suite), ADR-016 (graduation gate), ADR-036 (null calibration)
- **Relates to**: ADR-033, ADR-035 (both established the "record it, do not gate on it yet" pattern)

## Context
QuantForge's headline claim — the one in `CLAUDE.md`, in `ARCHITECTURE.md`, and in every
description of the project — is that it validates strategies with **PBO, purged CV, walk-forward,
and Deflated Sharpe**. Three of those are real. Walk-forward is not.

`app/validation/walk_forward.py::walk_forward_splits` and `purged_cv.py::purged_kfold_splits`
produce correct, Hypothesis-tested index splits: expanding train windows with
`max(train) < min(test)`, and purged K-fold with an embargo. Both are then used by
`ValidationEngine.validate` like this:

```python
n_walk_forward_splits=len(walk_forward_splits(n_obs, self._walk_forward_count)),
n_purged_folds=len(purged_kfold_splits(n_obs, self._purged_folds, self._embargo)),
```

The engine computes the split geometry and records **how many splits there would be**. Nothing is
ever selected on a training block or scored on a test block. `ValidationReport` then carries two
integers that a reader — and the dashboard that renders them — will reasonably read as "walk-forward
validation was performed". It was not. This is the single largest gap between what the repository
claims and what it computes, and it sits in the component whose entire purpose is honesty.

The gap also leaves a real question unanswered. Every out-of-sample number in the system today comes
from **one** locked holdout at the end of the series (ADR-015/016). That measures one config, chosen
using the whole search set, against one regime. It cannot distinguish "this parameterization works"
from "*re-selecting* a parameterization periodically works", and the second is what a live operator
actually does. Walk-forward is precisely the prequential procedure that answers it: select on data
you had at the time, score on what came next, repeat, and average.

## Decision
**Evaluate the walk-forward splits and record the result on every `ValidationReport`. Do not gate
on it yet.**

### What is computed
`walk_forward_evaluate(performance, splits) -> WalkForwardResult`, where `performance` is the same
`(T observations, N configurations)` per-bar return matrix `ValidationEngine.validate` already
builds for PBO. For each split:

1. Select the config with the highest Sharpe **on the training rows only** (`argmax`, ties → lowest
   index, so the result is deterministic).
2. Record that config's train Sharpe (in-sample) and its Sharpe on the **test rows** (out-of-sample).

The result carries per-split `selected_config`, `is_sharpe`, `oos_sharpe`, plus:

- **`mean_oos_sharpe`** — the headline. A prequential estimate of what the *selection procedure*
  delivers, averaged over several disjoint forward windows and therefore several regimes.
- **`efficiency`** — Pardo's walk-forward efficiency, `mean_oos_sharpe / mean_is_sharpe`. Defined
  **only when `mean_is_sharpe > 0`**, and `None` otherwise: a ratio of two negative Sharpes is
  positive and would read as "efficient" when both halves lost money. Refusing to define it is the
  honest answer, consistent with rule 6 (flag, never silently default).
- **`consistency`** — the fraction of splits with `oos_sharpe > 0`. Catches the case where one
  spectacular window carries a mean that every other window contradicts.
- **`n_splits`** — the count `ValidationReport.n_walk_forward_splits` carried on its own
  before, now attached to the numbers it describes. The existing top-level field stays: it is
  a required member of the frontend's Zod contract and is rendered today.

`ValidationReport.walk_forward` is a new nullable field (`WalkForwardResult | None`), additive and
defaulted, so the 3,227 experiments already in the pool deserialize unchanged.

### Why reusing the performance matrix is sound, and what it does and does not prove
No strategy is re-backtested per split; the train/test blocks are row slices of the matrix. This is
valid **because every catalog strategy is causal** — its signal at bar *t* is a function of bars
≤ *t* only (trailing rolling windows, `shift(1)`, recursive EMAs; documented per strategy and
enforced by the engine's `position.shift(1)`). A causal series sliced at row *k* is identical to the
series that would have been produced by running only on rows `[0, k)`, up to warm-up.

This matters for cost: a full-catalog search is ~23 s of CPU, and re-backtesting `n_splits`
times per strategy would multiply the discovery workflow's cloud time by ~5 for information that a
row slice already contains.

Being precise about the claim: **what walks forward here is the *selection*, not the fitting.** The
catalog's strategies have no fitted state to re-estimate — a parameter set is chosen, not trained —
so selection is the only thing there is to walk forward, and it is exactly the step that multiple
testing corrupts. A future strategy family with genuinely fitted state (a meta-label model, ADR-034)
could not use this shortcut, and this ADR does not license it to.

**Warm-up caveat, stated because it is the honest weakness:** the first split's training block
includes each config's warm-up bars, where positions are flat and returns are zero. That biases the
earliest in-sample Sharpes toward zero, and therefore `efficiency` slightly upward. It does not
touch `mean_oos_sharpe` or `consistency`, which is one more reason those two are the headline and
`efficiency` is not.

### Why not a gate — yet
Adding a walk-forward floor to `GateConfig` would change what graduates. Charter §4 allows a
threshold change only on argued methodology with evidence, and there is no evidence yet: no
experiment in the pool has ever had a walk-forward number computed, so no one knows what value
separates signal from noise here. Guessing a floor now would be exactly the "tune it because the
funnel felt empty" move the charter forbids, run in reverse.

The evidence is obtainable and the machinery for it already exists. ADR-036/037's null calibration
runs the unmodified search over symbols with **no edge by construction**. Once
`walk_forward_evaluate` is on the report, a null run measures the distribution of `mean_oos_sharpe`
and `consistency` under a known-zero edge — which is the principled way to site a threshold, rather
than an eyeballed rule of thumb.

**Trigger for revisiting (measurable, no re-derivation needed):** after one full null-calibration
run at N ≥ 200 per mode carries walk-forward numbers, compare the null's `mean_oos_sharpe`
distribution against the pool's gate-passing experiments. If the pool's passers are not separated
from the null at the 95th percentile, a walk-forward floor set at that percentile is justified and
gets its own ADR.

### Purged CV
`n_purged_folds` is the same species of decorative count, but it is **deliberately left as-is here**.
Purged K-fold is a *non-sequential* resampling scheme; scoring a causal price strategy on
non-contiguous folds requires deciding how to treat the discontinuities at every fold boundary, and
that decision deserves its own ADR rather than being smuggled into this one. What this ADR does fix
is the report no longer being *only* counts. Purged CV's honest status — geometry that nothing
consumes, retained because ADR-008 specified it and the embargo logic is correct and reusable — is
now recorded here rather than being invisible.

## Alternatives considered

1. **Re-backtest each strategy per walk-forward window.** The textbook implementation, and
   unnecessary here: causal strategies make a row slice equivalent, and the cost is ~5x the
   discovery workflow's CPU. Would be required for a family with fitted state.
2. **Gate on walk-forward efficiency immediately.** Rejected: no evidence for a threshold, and it
   would make every future experiment incomparable with the 3,227 already in the pool, for a gate
   that currently admits zero deflation-bar survivors anyway.
3. **Delete the two count fields and drop the walk-forward claim.** Honest, and cheaper. Rejected
   because walk-forward genuinely is the right procedural measurement for this system, and the
   splitter needed to compute it was already written and tested — the gap was the last 30 lines.
4. **Report `mean_oos_sharpe` only, and skip efficiency/consistency.** Rejected: a mean over ~5
   windows with no dispersion measure is the exact statistic this project criticizes elsewhere.

## Consequences
- `ValidationReport` gains one nullable field; the API response and Zod contract widen additively.
- Every validated strategy now carries an out-of-sample estimate that is **not** the locked holdout,
  giving the gate's holdout number an independent cross-check for the first time.
- Nothing that graduates today changes. This ADR adds a measurement, not a verdict.
- The null-calibration workflow (ADR-037) transparently picks the new numbers up, since it runs the
  unmodified search.

## Reversal
Delete `walk_forward_evaluate` / `WalkForwardResult` from `app/validation/walk_forward.py`, drop the
`walk_forward` field from `ValidationReport`, and restore `n_walk_forward_splits` in
`ValidationEngine.validate`. Nothing gates on the new field, no stored data depends on it (it is
nullable and defaulted), and the graduation semantics are byte-identical with or without it.
