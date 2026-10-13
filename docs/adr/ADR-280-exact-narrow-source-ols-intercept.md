# ADR-280: Compute narrow-source alpha from the exact represented OLS intercept

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** Codex autonomous session 8, ISO 2026-W42
- **Resolves:** FINDING-229
- **Prerequisite:** ADR-278, ADR-279
- **Extends:** ADR-276's unrounded-intercept principle to a separate bounded family

## Context

For float32 or classic masked Float32 benchmark .1 plus three consecutive native
ULPs and strategy benchmark plus one ULP, exact OLS beta is one and annual alpha
is 1.8775463104248047e-6. The public comparator publishes beta1/alpha0 because
source means round in narrow precision. Native float16 at n4 likewise publishes
alpha0 instead of .015380859375. Promoted dispersion in ADR-279 does not fix
source means. Rounded published beta can independently amplify intercept error.

## Options considered

1. Separate exact common-grid integer sufficient sums for both-original narrow
   float sources, with only one final intercept conversion. Keep published beta.
2. Stable source means but rounded beta. Still rounds mean residuals and beta
   before intercept cancellation; weaker than the demonstrated coefficient contract.
3. Anchored float64 intercept. Better conditioned but retains cancellation roundoff.
4. Generalize all comparator source statistics or existing integer helpers. Larger
   compatibility surface without evidence requiring it.

## Decision

Only when BOTH original aligned source dtypes are native float16/float32 or
classic pandas Float32Dtype, compute annual alpha from an exact unrounded OLS
fit. Preserve all published beta arithmetic and outputs. The family deliberately
adopts exact coefficient rounding even where prior narrow alpha was finite.

Each source observation has an exact integer encoding on the fixed 2**-149 grid;
float16's entire range is contained. Use each scalar's as_integer_ratio and exact
Python integer multiplication by 2**149 divided by its power-of-two denominator.
Accumulate own-first deltas and the same covariance sufficient sums as ADR-275:
num=n*sum(ds*db)-sum(ds)*sum(db), den=n*sum(db*db)-sum(db)**2.
With original encoded totals S and B, alpha is the single final quotient
252*(S*den-num*B)/(n*den*2**149). Require a positive denominator. Do not allocate
object Series or alter the accepted integer helpers. This is O(n) time and O(1)
additional memory; no caching or intermediate floating arithmetic is needed.

If either source is exactly constant, retain beta-zero convention and calculate
only the exact strategy mean: 252*S/(n*2**149), without covariance work.
Existing source guards and constant detection still precede this boundary.
Integer, float64, wider, third-party and mixed narrow/other-source alpha paths
remain unchanged. Excess subtraction/moments/metadata, drawdown and caller state
stay. No threshold, calibration identity, workflow, schema or generated record
changes. Alpha need not equal rounded published beta times rounded means:
it is the same mathematical OLS intercept calculated before those roundings.

## Evidence and limits

Independent pre-code common-grid and streaming prototypes passed 1,008 centered
Fraction oracles over nine ordered dtype pairs, n2–128, constants, full-width
values and tiny/large scales. 100,000 observations took about .136 seconds.
Encoded observations are below 2**277 in magnitude; for n<=sys.maxsize on 64-bit,
conservative exact intermediates stay below about 1024 bits. A nonzero final
rational alpha is at least 2**-895 before annualization. The Float32 lattice
bounds maxabs benchmark / nonzero benchmark range below 2**25, which bounds
alpha below 2**230. Thus final alpha remains normal finite float64 in this family.
These are range bounds, not whole-comparator availability guarantees.

Require genuine repository RED before implementation, Fraction/Hypothesis and
full-width helper tests, independent final review, complete outside-family and
inside-family other-statistic preservation, foreground make check-all and exact
master CI. Source beta retains its separate rounding; already-rounded excess,
unsupported float16/masked-byte-integer subtraction and strict other arithmetic
remain separate limits. No historical market contamination is established.

## Reversal

Remove the narrow alpha helper and both-original dispatch. This reopens
FINDING-229 and preserves ADR-278/279 and the accepted integer intercept path.
