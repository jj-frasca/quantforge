# ADR-360: Qualify displayed rank IC as selected-sample screening evidence

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Codex autonomous session 29, ISO 2026-W43
- **Extends:** ADR-035, ADR-267
- **Resolves:** FINDING-300 (presentation scope only)
- **Supersedes:** ADR-035's inference that not selecting on IC removes selection bias

## Context

The dashboard says IC tells whether the ranking carried information, but omits
the backend's independent-period assumption and the current producer's selection
scope. Each family first chooses its maximum in-sample portfolio Sharpe, then
summarizes that finalist's rank IC on the same search sample. Not selecting on IC
does not make this selected-sample diagnostic independent validation. No measured
market bias, false graduate or significance error is established by this review.

## Options Considered

1. **Qualify the existing presentation and methodology documentation.**
   - Pro: communicates the actual computation without changing stored evidence.
   - Con: leaves dependence-aware inference and independent IC measurement open.
2. **Add a dependence-adjusted t-statistic or holdout IC now.**
   - Pro: could measure a more useful, separately attributed diagnostic.
   - Con: requires a new estimator, lag/sample policy and independent evidence;
     neither correction follows from a presentation review.
3. **Keep only the existing diagnostic-not-gate label.**
   - Pro: smallest display.
   - Con: conceals assumptions needed to interpret the displayed t-statistic.

## Decision

Describe IC as signal/next-return rank association. Explicitly attribute the
current producer to the family finalist selected by in-sample Sharpe on the search
sample; do not infer this provenance for arbitrary historical scalar records.
State that the t-stat assumes independent periods, with no serial-dependence or
search-selection adjustment. Call it screening evidence, not independent
validation or a graduation gate. Qualify the existing t-stat column heading.
Retain every served number, missing-value convention, server verdict, API/schema,
estimator, threshold, fingerprint and longitudinal accounting-v14 identity.
Keep existing walk-forward and purged-CV captions unchanged. Accepted ADR-035
remains historical; this ADR supersedes its no-selection-bias inference only.

## Consequences

Readers can distinguish descriptive association from independent inference.
The display is longer and does not repair or quantify dependence/selection bias.
Deterministic permuted IC sequences with identical summaries but different lag-1
correlations demonstrate chronology blindness only; they do not estimate market
error rates. No calibration/cohort execution or generated record change is needed.
RTL tests must require the qualifications alongside unchanged measured and absent
values. Run the full foreground gate and verify exact master CI after delivery.

## Reversal

Restore the previous copy/header and documentation, reopening FINDING-300.
Scientific computation and durable evidence remain unchanged either way.
