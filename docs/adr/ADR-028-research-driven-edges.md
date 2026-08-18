# ADR-028: Research-driven edges — Alpha101 factors, multi-factor composite, meta-labeling proposal

- **Status**: Accepted (Alpha101 + composite). The meta-labeling proposal is RESOLVED — declined by ADR-034 until a primary graduate clears the ADR-018 universe-deflation bar.
- **Date**: 2026-08-04
- **Deciders**: Joe Frasca
- **Extends**: ADR-024 (cross-sectional dimension), ADR-026 (maximum discovery)

## Context
Joe asked to find "new ways to gain an edge" and to look at what is working externally. A scan of
current systematic-trading practice (2025–2026) surfaced three techniques that fit QuantForge's
architecture and, crucially, our non-negotiable honesty gate:

1. **Formulaic cross-sectional alphas (WorldQuant "101 Formulaic Alphas", Kakushadze 2016).** A
   public library of 101 short-horizon alphas expressed as panel formulas over price/volume/vwap
   with cross-sectional `rank(...)` operators. They are exactly the shape our `cross_sectional`
   module already consumes (a dates×symbols signal panel, ranked into dollar-neutral legs), need no
   new dependency, and each is independently testable.
2. **Multi-factor composite / learning-to-rank.** Ranking on a *combination* of factors (rather than
   one) is reported to lift risk-adjusted returns materially (learning-to-rank ≈ 3× Sharpe vs a
   single sort in the cited work). The honest, dependency-free first step is a **z-score composite**:
   standardize several existing factors cross-sectionally each day and rank on their average.
3. **Meta-labeling / "corrective AI" (López de Prado 2017).** A *secondary* model that takes the
   primary strategy's signal and predicts whether to act on it (and how big), separating side from
   size. It suppresses false positives and is reported to lift precision sharply. This requires an ML
   classifier + triple-barrier labels + purged CV.

## Decision
**Accepted now (no new dependency, fed straight to the existing gate):**
- Add a batch of **Alpha101 cross-sectional factors** as new signal producers in
  `cross_sectional/strategies.py` + registry entries, starting with the simpler, high-signal,
  low-nesting formulas (e.g. #101 `(close-open)/(high-low)`, #12 `sign(Δvolume)·-Δclose`, #21/#41/#54
  families) implemented with pandas/numpy. Each is judged by the unchanged DSR/PBO/holdout gate.
- Add a **multi-factor z-score composite** cross-sectional strategy: cross-sectionally standardize a
  configurable set of the existing factors (momentum, low-vol, 52w-high, residual momentum, value)
  each date and rank on the mean z-score. Dependency-free; the honest precursor to learning-to-rank.

**Proposed (NOT built without Joe's blessing) — meta-labeling / ML layer:**
- A secondary classifier that filters/sizes a primary graduate's signal, trained with triple-barrier
  labels under purged K-fold CV. This needs **scikit-learn** (or a numpy logistic-regression to stay
  dependency-free) and a new `research/ml/` tree, and it is overfitting-prone, so it gets its own ADR
  and a strict validation protocol before any implementation. Recorded here as the next frontier.

### Honesty (unchanged)
None of this weakens the gate. New factors and the composite are just more candidates funnelled
through the same DSR/PBO/MinTRL/holdout/beat-benchmark bar (and universe deflation scales with the
count). Meta-labeling, if approved, must clear a purged-CV protocol designed against its known
overfitting failure mode before it is trusted.

## Options Considered
- **Jump straight to ML/learning-to-rank.** Rejected for now — highest overfitting risk, needs a
  dependency + a careful CV protocol; do the dependency-free composite first and prove the plumbing.
- **Only add more single-name indicators.** Rejected as the primary move — the catalog already has
  34; the marginal edge is in *different constructions* (cross-sectional formulaic alphas, factor
  combination), not another oscillator.

## Consequences
- More, genuinely different alpha sources for the cross-sectional hunt to test — honest breadth.
- A clear, staged path to the higher-ML techniques (composite → learning-to-rank → meta-labeling),
  each gated behind evidence and (for the ML step) an explicit dependency decision.

## References
- Kakushadze, "101 Formulaic Alphas" (2016): https://arxiv.org/pdf/1601.00991
- Building Cross-Sectional Systematic Strategies by Learning to Rank (PM Research, 2025):
  https://www.pm-research.com/content/iijjfds/3/2/70
- ML-Enhanced Multi-Factor Cross-Sectional Optimization (arXiv 2507.07107, 2025):
  https://arxiv.org/html/2507.07107
- López de Prado meta-labeling (overview): https://en.wikipedia.org/wiki/Meta-Labeling

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*
