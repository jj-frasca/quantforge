# ADR-212: Verify subnormal Sortino with an exact squared oracle

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 15, ISO 2026-W41
- **Addresses:** FINDING-154
- **Extends:** ADR-210's verification boundary

## Context

F154 proves that the new Decimal800 test oracle cannot certify exact halfway
subnormal rounding. It also exposes a one-output-ULP production precision limit
when a negative residual contributes an unrepresentably tiny downside square.
The new property's relative-only assertion claimed precision that double
arithmetic and the oracle did not establish.

## Decision

Correct only the independent test oracle and its precision claim. From exact
Fraction observations compute `Q = 252 * sum(values)**2 / (n * sum(shortfall**2))`.
For subnormal-range scores, express Q in squared smallest-subnormal units; use
integer square root and exact rational midpoint comparison to select the nearest
integer unit with ties-to-even. Normal-range Decimal800 relative checks remain.

Keep full new sample-count/exponent/sign domains and every original engine
financial property domain. Require nonzero scores and correct signs throughout.
At the subnormal boundary measure a one-output-ULP error budget with exact rational
distance; retain 5e-14 relative checks in the normal range. This is the corrected
finite-precision assertion, not a changed graduation or validation threshold.
Existing explicit 3/100-observation exact fixtures remain unchanged.

Add positive/negative 112-observation exact-rounding oracle regressions, observing
the positive oracle failure first. Document the negative production discrepancy;
no correctly-rounded production guarantee follows. No production source, metric
definition, gate threshold, calibration identity v10, generated record, workflow
or paid resource changes.

## Verification

Independent Fraction proof, RED oracle fixture, full-domain Hypothesis checks,
bounded subnormal error audit and full foreground gates precede delivery.

## Reversal

Restore the Decimal-only subnormal oracle and relative-only assertion. This
reintroduces a false halfway oracle and unsupported precision claim.
