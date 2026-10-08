# FINDING-154: Decimal subnormal Sortino oracle misrounds a halfway score

- **Date:** 2026-10-07
- **Severity:** Medium — false verification and an unsupported precision claim
- **Status:** Oracle corrected by ADR-212; measurement limit documented

## Evidence

For 112 observations `[-1, smallest_subnormal, 1]` plus 109 zeros, the exact
Sortino squared score is `(252/112) * smallest_subnormal**2`. Its magnitude is
exactly 1.5 subnormal units; binary64 ties-to-even correctly rounds to two units.
The new Decimal800 test helper instead rounds to one unit because separate
irrational square-root rounding puts the computed intermediate below the tie.
More decimal digits alone do not establish the side of an exact halfway value.

With the residual negative, downside squared sum includes the residual's square.
The exact magnitude is infinitesimally below 1.5 units and correctly rounds to
one unit. Native float recovery loses that tiny square and measures two units:
this is a real one-output-ULP precision limitation, consistent with ADR-210's
explicit absence of a universal correctly-rounded guarantee. Both scores remain
nonzero and retain their signs. These are independent exact Fraction proofs;
no graduate or gate effect is asserted for descriptive Sortino.

## Verification boundary

Keep every original engine property domain and the new property's full sample-
count/exponent/sign domain. Use exact rational squared-score comparisons against
binary64 midpoint squares for subnormal oracle rounding. Measure output error in
subnormal units rather than claiming 5e-14 relative accuracy at a one-unit value.
Normal-range relative checks, nonzero/sign requirements, existing exact fixtures,
gate thresholds and production formulas remain unchanged. Record the numerical
measurement limit plainly; do not relabel it as correctly rounded output.

## Verification

Both signed 112-observation oracle fixtures fail before correction. Exact
Fraction squared-score midpoint selection makes them pass and retains every
explicit exact 3/100 case. A bounded complete audit of 18,900 binary residual
cases (n=3..128, gap=1000..1074, both signs) observes maximum subnormal error of
one output unit; all normal-range relative checks and nonzero signs pass. Binary
source scaling preserves these normalized samples exactly. This is bounded
evidence for the written limit, not arbitrary-input accuracy certification.
