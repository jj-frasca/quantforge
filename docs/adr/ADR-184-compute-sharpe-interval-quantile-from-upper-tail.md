# ADR-184: Compute Sharpe interval quantiles from the upper tail

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 11, ISO 2026-W41
- **Resolves:** FINDING-118
- **Extends:** ADR-109, ADR-111, ADR-183

## Context

The valid confidence immediately below one makes 0.5+confidence/2 round to one. norm.ppf then
returns infinity, although the requested confidence has a finite Gaussian quantile. Nearby finite
CDF arguments can also lose relative precision in the small upper-tail probability.

## Options Considered

1. Evaluate the equivalent inverse survival function at (1-confidence)/2. The small tail remains
   representable and the interval's mathematical definition is unchanged.
2. Cap confidence below its existing upper boundary. Arbitrarily changes the accepted domain.
3. Reject nonfinite output. Avoids invalid publication but unnecessarily declines a finite answer.

## Decision

Use norm.isf((1-confidence)/2) for the positive Gaussian quantile. This is mathematically identical
to norm.ppf((1+confidence)/2), without subtracting its tiny tail through a rounded CDF argument.
Keep confidence validation, complete-sample checks, one-year minimum, annualization, Sharpe and
standard-error formulas, symmetric bounds and iid_normal metadata. No new confidence cap.

## Consequences and limits

nextafter(1,0) yields finite symmetric bounds. A forward erfc survival-probability oracle verifies
requested high-confidence tails without a loose absolute tolerance that hides small probabilities.
Existing ordinary-confidence/default interval oracles remain valid. This is numerical evaluation
of the same estimator, not robust dependence coverage or a threshold change. Very small confidence
and interval widths below endpoint resolution remain separate floating-point limitations.
No generated data, calibration identity, gate or workflow changes.

## Reversal

Restore the rounded CDF argument. This reopens FINDING-118.
