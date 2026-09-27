# ADR-139: Bind forward decisions to quality-checked evidence

- **Status:** Accepted
- **Date:** 2026-09-27
- **Deciders:** Codex autonomous session 29 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-070
- **Extends:** ADR-006, ADR-019, ADR-020, ADR-021, and ADR-137

## Context

The single-name discovery path now carries an immutable `ResearchDataset` from vendor acquisition
through the durable experiment, but its out-of-time continuation does not. Daily forward scoring,
lifecycle exits, and Alpaca paper target sizing accept plain DataFrames produced directly from fresh
adapter bars. Those are new scientific and paper-execution decisions, not passive displays, and the
persisted score contains no recoverable evidence identity.

## Options Considered

1. **Reuse `ResearchDataset` and persist a frozen evidence projection with each score.**
   - Pro: applies the existing ADR-006 boundary to the exact forward input and makes each durable
     score self-contained.
   - Con: changes provider interfaces and adds nullable compatibility data to the score.
2. **Quality-check only in live scripts and keep pure orchestration frame-based.**
   - Pro: fewer model changes.
   - Con: tests and future callers can bypass the contract, and persisted results still cannot prove
     which evidence supported them.
3. **Look up the latest quality report after scoring.**
   - Pro: avoids carrying metadata through the computation.
   - Con: races overlapping fetches and invents lineage after the decision.

## Decision

Every production single-name forward provider returns a passed `ResearchDataset`. Managed scoring
and broker target orchestration accept that type rather than a plain DataFrame. A frozen
`ResearchDatasetEvidence` projection contains the complete `DataQualityReport`, source, adapter
version, requested half-open range, and executed git revision; every new non-empty forward score
persists that projection. Legacy and zero-bar scores may retain absent evidence.

Provider or quality failures remain fail-soft at the managed-book level: the affected position is
left unchanged while other positions continue. Broker target construction fails closed for that
name and emits no target. The adapter, strategies, lifecycle thresholds, sizing math, and paper-only
broker restriction do not change.

Cross-sectional forward panels require their own decision because a frozen factor depends jointly
on a fixed universe; ADR-139 does not treat a changing set of single-name datasets as one panel.

## Consequences

- A lifecycle hold/exit and its latest score identify the exact checked vendor evidence used.
- A paper order target cannot be computed from a plain or failed-quality frame.
- Existing persisted books remain readable without fabricated provenance.
- Production scripts share the same acquisition boundary as ADR-137 discovery.

## Reversal

Restore DataFrame providers and remove score evidence. This would again permit unvalidated,
unattributed forward and paper-order decisions and is not recommended.
