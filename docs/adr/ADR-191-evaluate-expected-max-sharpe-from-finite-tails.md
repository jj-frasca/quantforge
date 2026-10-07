# ADR-191: Evaluate expected-max Sharpe from finite tails

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 11, ISO 2026-W41
- **Resolves:** FINDING-126
- **Extends:** ADR-050, ADR-054, ADR-190

## Context

Large finite trial counts make both expected-max Gaussian CDF arguments round to one, publishing
an infinite threshold even though its mathematical quantiles are finite. Finite dispersion scaling
can independently overflow the final haircut. Source-validity checks do not fix either limitation.

## Options Considered

1. Evaluate the same quantiles from upper tails and decline nonfinite derived thresholds.
2. Cap trial counts, dispersion or the final haircut. Alters multiplicity pricing.
3. Reject every large count affected by CDF cancellation. Declines representable valid answers.

## Decision

After shared source validation and the valid N=1 shortcut, compute tail_a = 1 / n_trials using
integer true division, then tail_b = tail_a / e. Integer division supports representable reciprocals
of counts beyond float's maximum, unlike 1.0 / n_trials or n_trials * e. Require both tails to be
positive finite; refuse unrepresentable tails with ValueError. Evaluate a=norm.isf(tail_a) and
b=norm.isf(tail_b), then the same weighted dispersion-scaled expected maximum. Require that final
threshold to be finite, otherwise ValueError. Keep source checks, count, dispersion, weighting,
N=1, margin clamp and PSR formulas; impose no arbitrary accounting caps.

## Consequences and limits

Mathematically finite quantiles no longer become infinite from CDF rounding. Unrepresentable tails
or scaled haircuts are unmeasurable rather than published infinity. RED tests precede correction;
independent brentq inversion of forward math.erfc tails verifies large counts, including 10**309.
Ordinary estimates may show small floating-point differences but use the same mathematical
estimator, hypothesis counts and selection policy. CDF cancellation differences grow with count. This numerical evaluation does not advance calibration procedure
identity or change any threshold; existing ordinary-scale/reference/property tests retain coverage.
Very small positive subnormal-tail rounding and PSR arithmetic remain separate precision limits.
No generated records, workflows, paid services or cloud resources change.

## Reversal

Restore rounded CDF arguments and unchecked scaling. This reopens FINDING-126.
