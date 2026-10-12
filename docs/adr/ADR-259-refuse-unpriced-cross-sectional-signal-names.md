# ADR-259: Refuse unpriced cross-sectional signal names

- **Status:** Accepted
- **Date:** 2026-10-12
- **Deciders:** Codex autonomous session 2, ISO 2026-W42
- **Resolves:** FINDING-208
- **Extends:** ADR-024, ADR-025
- **Relates to:** ADR-138, ADR-140, ADR-257

## Context

portfolio_returns ranks the complete supplied signal panel, then projects the
weights onto price columns. An unpriced name can win one leg and disappear during
projection, leaving a directional portfolio presented as dollar-neutral. Standard
production generators retain price columns; this is a public-kernel boundary
finding, without evidence of historical production contamination.

## Options Considered

1. Refuse any signal column absent from prices before ranking.
   - Pro: every ranked leg has price evidence without changing valid ranks.
   - Con: malformed direct callers must correct their supplied universe.
2. Project signals onto prices and rerank.
   - Pro: yields neutral legs on the available panel.
   - Con: silently changes the submitted strategy and tie/quantile membership.
3. Trust production signal generators.
   - Pro: no extra public guard.
   - Con: direct callers can publish directional returns under a neutral claim.

## Decision

After the original cost checks and before long_short_weights, require every
supplied signal column to occur in prices.columns. Refuse extra names with
ValueError, including empty histories and all-NaN extra columns. Preserve the
original signal frame, its supplied tie order, sparse dates, subset columns and
NaN warmup semantics. Missing priced names still receive original zero weights.
Keep ranking, projection, lag, turnover and return formulas unchanged.

This is membership only: it adds no column normalization, complete-universe,
calendar, dtype, duplicate-name or general signal-causality policy. No estimator,
threshold, calibration identity or generated record changes.

## Verification and reversal

Observe malformed-universe RED tests before production edits, including lost
long/short legs, empty/flat histories and refusal before ranking. Preserve exact
subset/reordered/sparse/native results and verify a Hypothesis adversarial ranked
leg invariant. Require independent review and foreground make check-all before
commit/push; watch exact master CI. Remove the membership guard to reverse this
correction and reopen FINDING-208.
