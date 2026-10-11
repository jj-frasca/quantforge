# ADR-240: Validate the original legacy AR reference coefficient

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 31, ISO 2026-W41
- **Resolves:** FINDING-189
- **Extends:** ADR-041, ADR-223, ADR-230, ADR-233

## Context

The legacy AR scorer multiplies phi by lagged returns before checking original
coefficient evidence. NaN phi becomes all-missing predictions and a finite zero
score. Infinite phi on flat prices also becomes missing and scores zero. Boolean
phi produces numeric predictions and finite reference scores. The generic
prediction guard cannot identify provenance erased by multiplication.

## Options Considered

1. Validate original phi before return/prediction construction. One narrow call,
   preserves native multiplication but rejects malformed direct callers.
2. Trust derived predictions. Misses NaN and infinite-coefficient flat forecasts.
3. Coerce, replace or restrict phi to stationarity. Changes original operands or
   existing finite caller domains; rejected here.

## Decision

Call the shared original finite float-representable real nonboolean scalar guard
before _reference_returns in oracle_sharpe. Ignore its converted return and retain
original phi in the existing multiplication. Original invalid phi now precedes
source/delegated-cost errors on combined malformed calls. With valid phi retain
existing source-before-delegated-cost order. No new stationarity range is added;
existing finite coefficients outside (-1,1) retain their reference sign scores.

Preserve valid native types, lag/startup/missing conventions, return/cost math,
reference defaults, thresholds, fingerprints and generated artifacts. General
unsupported mixed-type multiplication remains separate. This original-evidence
correction does not add the omitted drift intercept or production attribution;
FINDING-155 remains Open, as do FINDING-159's separate band qualifications.

## Verification

Observe invalid original coefficients on empty, singleton and varying sources
before code; include infinite coefficients on flat prices. Protect signed/zero
coefficients, finite values outside stationarity, native NumPy callers, startup
and documented source/cost precedence. Include Hypothesis boolean refusal and
positive sign-scale invariance. Independent review compares native gross/net
scores and unchanged executable arithmetic after removing the validation call.
Full foreground make check-all and exact master CI precede completion.

## Consequences and reversal

Invalid original coefficients cannot disappear into flat forecasts while obtaining
reference claims. Removing the one call reopens FINDING-189; no historical source,
score or power outcome is restated.
