# ADR-027: Modest gate calibration — widen the funnel via parameter-stability only

- **Status**: Accepted
- **Date**: 2026-08-04
- **Deciders**: Joe Frasca
- **Extends**: ADR-015 / ADR-016 (graduation gate + versioned `GateConfig`)

## Context
The graduation gate is deliberately strict, and rightly so — it is the honesty core. But at ~1 month
of forward data the managed paper book is thin (only a handful of strategies are live at any time,
mostly mean-reversion sitting flat), so we are learning slowly. Joe's direction: let a few more
graduate "by a little bit" to gather more forward-test signal, **without** compromising rigor.

The gate has two kinds of thresholds:
- **Core statistical anti-overfitting bars** — Deflated Sharpe > 0 (survives multiple-testing),
  PBO < 0.5 (in-sample best isn't OOS-below-median), MinTRL (track record vs trials), locked-holdout
  Sharpe > 0, and beat-buy-and-hold (the edge isn't just beta). These are the mathematics of "is
  this real?" and are NOT negotiable.
- **A policy quality knob** — `stability_min`, the parameter-stability score (how sensitive the edge
  is to small parameter changes). This is a robustness *preference*, not a survival test.

## Decision
Relax **only** the policy knob: `GateConfig.stability_min` from **0.5 → 0.4**. Every core statistical
bar is unchanged. A strategy must still clear DSR > 0, PBO < 0.5, MinTRL, holdout Sharpe > 0, and
beat buy-and-hold; it may now be marginally more parameter-sensitive (stability in [0.4, 0.5)).

This widens the funnel a little — enough to deploy more capital and gather more forward-test data —
while the claim "graduation means a statistically real, out-of-sample edge that beats holding the
name" is fully preserved. The change is versioned (`GateConfig.version_hash`), so every experiment
records the exact rubric that judged it and the calibration loop can compare 0.4-era vs 0.5-era
outcomes; it is trivially reversible.

## Options Considered
- **Lower a core bar** (DSR/PBO/holdout/beat-B&H). Rejected outright — that would let through results
  that are plausibly luck, which is the one thing we never do.
- **Only add more discovery, don't touch the gate.** Considered; we are ALSO doing this (broader
  universe, more shots — the honest lever of ADR-026). But Joe explicitly asked to widen graduation
  a little, and stability is the safe knob to do it with.
- **Bigger stability drop (e.g. 0.3) or remove it.** Rejected — 0.4 is a modest, reversible step; a
  large drop would admit genuinely fragile, one-parameter-only fits.

## Consequences
- A few more strategies graduate per hunt (the marginally-less-stable ones that already clear every
  statistical bar), deploying more paper capital and producing more forward-test data to learn from.
- The honesty guarantee is intact: no result graduates that fails the multiple-testing, PBO,
  holdout, or beat-benchmark tests. Only the parameter-robustness preference is looser.
- Watch item: track whether 0.4-era graduates underperform 0.5-era ones out-of-sample (the version
  hash makes this measurable). If they do, revert — the calibration loop is exactly for this.

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*
