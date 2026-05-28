# ADR-008: Validation-first philosophy

- **Status**: Accepted
- **Date**: 2026-05-28
- **Deciders**: Joe Frasca

## Context
Most published/backtested strategies are statistically invalid: with enough configurations
tried, an impressive in-sample Sharpe is almost guaranteed by chance (Bailey et al. 2015).
QuantForge's credibility — its actual recruiting signal — rests not on strategy count or
returns, but on **rigorously quantifying overfitting and deflating performance claims**. The
validation engine is therefore the centerpiece, not an afterthought.

## Options Considered
1. **Validation-first: every strategy result is accompanied by PBO, purged CV, walk-forward,
   and a Deflated Sharpe, and a strategy is not "promising" until it survives them.**
   - Pro: matches the López de Prado / Bailey methodology that quant researchers respect;
     turns "here's a backtest" into "here's a backtest and here's why you should/shouldn't
     believe it"; the validation layer is reusable across strategies and the ML model (Phase 7).
   - Con: more machinery before any strategy looks good; honest results are often discouraging.
2. **Backtest-only (report Sharpe/returns, skip validation).**
   - Pro: less work; prettier headline numbers.
   - Con: statistically dishonest; exactly the failure mode the project exists to counter.
     Rejected.

## Decision
**Validation-first.** The backtest engine's oracle tests must pass before any validation runs
(a statistic on a buggy engine is worthless). Then every strategy is run through the validation
engine to produce a `ValidationReport` (PBO, Deflated Sharpe, walk-forward, purged CV). Each
validator encodes its mathematical invariant as a Hypothesis property test. A random strategy
must yield PBO ≈ 0.5 and a Deflated Sharpe ≤ its observed Sharpe — the engine is calibrated to
say "this is noise" when it is.

## Consequences
- The `ValidationReport` is the MVP deliverable (Phases 1–4 + the frontend page that renders it).
- Validation operates on returns/performance matrices in memory — no database required, so the
  engine is fully unit-testable and CI-gated.
- Results will often be unflattering; that honesty is the point (ARCHITECTURE.md §0, §2.4).
- The same validation layer is reused for the Phase 7 ML factor model ("I understand why
  financial ML usually fails, and here is how I detect it").
