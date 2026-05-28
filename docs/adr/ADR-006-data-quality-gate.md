# ADR-006: Data quality as a mandatory pipeline gate

- **Status**: Accepted
- **Date**: 2026-05-27
- **Deciders**: Joe Frasca

## Context
Backtests and validation are only meaningful on trustworthy data. Vendor OHLCV carries
splits and dividends, missing bars, stale quotes, single-bar anomalies, corporate actions,
and timezone inconsistencies. But **no automated check can guarantee data is correct** — every
check is a heuristic that produces false positives and false negatives. We need a structural
place to catch *likely* problems and make the result auditable, without overclaiming what the
checks prove. (See ARCHITECTURE.md §2.4 — Data Quality Honesty.)

## Options Considered
1. **A mandatory `DataQualityEngine` gate between ingestion and any downstream use.**
   - Pro: one chokepoint — nothing reaches research/validation on ungated data; the gate
     emits a `DataQualityReport(passed: bool, issues: [...])` that is persisted and linked
     from the `ExperimentManifest`, so a backtest's data provenance is reproducible.
   - Con: the gate can block ingestion; heuristics misfire, so some review is unavoidable.
2. **Validate ad hoc inside each consumer.**
   - Con: every consumer re-implements checks, they drift, and one forgotten check means
     research silently runs on bad data.
3. **No quality layer — trust the vendor.**
   - Con: splits/gaps/timezone bugs corrupt results invisibly; defeats the project's
     entire credibility premise (rigor).

## Decision
The **`DataQualityEngine` runs as a mandatory gate** after normalization and before storage
makes data available to any research or validation component. It runs 8 heuristic checks
(survivorship-bias risk flag, split/dividend consistency, corporate-action detection, missing
bars, price anomaly, stale data, timezone, vendor cross-validation) and produces a
`DataQualityReport` with `passed: bool` and a list of `DataQualityIssue`. **Every downstream
component MUST verify `passed is True` before using the data.**

Two deliberate caveats, encoded as rules:
- **Checks FLAG potential issues; they do not prevent or guarantee anything.** Docstrings and
  messages say "flags potential X", never "prevents/guarantees X" (CLAUDE.md rule 6).
- **Timezone is the one exception**: UTC coercion is *enforced at the model boundary* and a
  non-coercible timestamp raises `ValidationError` — it is not a soft flag.
- **Survivorship bias is a RISK FLAG only.** We do not solve it; real mitigation needs
  CRSP-style delisted-inclusive datasets unavailable via yfinance. The limitation is
  documented wherever survivorship bias is discussed.

## Consequences
- Each ingested series produces a persisted `DataQualityReport`; its id is recorded in the
  `ExperimentManifest` so results are reproducible against a known data-quality snapshot.
- False positives are expected and reviewed — the gate informs, it does not certify truth.
- The 8 checks and their thresholds are specified in `.claude/context/data-contracts.md` and
  enforced/known by the `data-engineer` agent.
- Adding a second vendor (Polygon, Phase 3) activates vendor cross-validation (check 8).
