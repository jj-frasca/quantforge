# ADR-283: Compute Float64 beta and alpha from exact represented OLS coefficients

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** Codex autonomous session 9, ISO 2026-W42
- **Resolves:** FINDING-232
- **Extends:** ADR-269, ADR-275/276's exact sufficient-sum principle

## Context

For native float64/classic pandas Float64 benchmark 2**60 + arange(4)*256
and strategy benchmark+256, the comparator accepts beta2/3 and annual
alpha9.684540638697531e19. Exact represented observations give beta1 and
alpha64512. Rounded large-origin centering corrupts both matched moments.
Repairing alpha alone would preserve a known false slope. Existing integer,
narrow-intercept and genuine-wide corrections deliberately exclude this family.

## Options considered

1. Exact common-grid integer covariance sums and coupled coefficients for both
   original Float64 sources. Exact represented coefficients and modest streaming
   cost; deliberately changes rounding throughout this family.
2. Anchored floating moments. Cheaper arithmetic but still loses cancellation
   and does not establish exact final intercept rounding across full widths.
3. Exact alpha only or stable means with rounded beta. Smaller diff, but retains
   the demonstrated false slope or amplifies slope rounding in the intercept.
4. Replace all source estimators. Broader consistency, unnecessary compatibility
   changes to the independently accepted integer/narrow/wider contracts.

## Decision

Only when BOTH original aligned source dtypes are native NumPy floating dtype
of float64 width or classic pandas Float64Dtype, calculate beta and annual alpha
from exact common-grid Python integer sufficient sums. Existing source/calendar/
alignment/finite/wealth checks and exact-source constant detection precede this.
Do not dispatch on a converted array, third-party dtype or observation magnitude.

Scan original scalar as_integer_ratio denominators to choose their maximum G.
Binary denominators divide this power-of-two grid exactly: encode p/q as p*(G/q).
For nonconstants accumulate own-first deltas ds/db and four streaming sums.
num=n*sum(ds*db)-sum(ds)*sum(db); den=n*sum(db*db)-sum(db)**2 must be positive.
Reconstruct encoded totals S/B. Beta is num/den; annual alpha is
252*(S*den-num*B)/(n*den*G), converting only those final integer quotients to float.
Compute both together, without intermediate means or rounded-beta substitution.
If either source is exactly constant, retain beta0 and exact strategy mean
252*S/(n*G), bypassing covariance accumulation.

Normalize final quotient OverflowError or nonfinite coefficients to ValueError.
Legitimate finite zero/subnormal rounding remains valid. No epsilon, cap, fallback,
source repair or native floating moments are needed in this coefficient path.
Integer/narrow/wider/mixed-other/third-party coefficient paths remain unchanged;
original excess, IR/TE, relative drawdown, metadata and caller state remain.
No validation threshold, calibration identity, schema, workflow or generated
record changes. These descriptive comparator coefficients do not select/gate.

## Evidence and limits

Independent precode reproduction: 252 Fraction finite coefficients, 32 exact
nonfinite refusals; additional 239 finite/161 overflow probes and four final
zero/subnormal controls. 100k rows cost .19s ordinary/.63s full exponent span.
Binary64 encoded values need about 2098 bits before translation; with n<=sys.maxsize,
conservative coefficient intermediates remain under about 6600 bits. Two streaming
scans are O(n) time, O(1) accumulator count, with no cache/object Series/Fraction
production values. Integer sizes grow logarithmically with row count.

Require observed public RED, independent centered Fraction/Hypothesis oracles,
full-width helper rounding/refusal controls, constants/guard precedence, alignment,
source/state preservation, complete outside-family and affected other-statistic
baseline comparisons, independent final review, foreground make check-all and
exact master CI. Family-wide coefficient rounding changes intentionally, including
previously adequate finite values. Alpha need not match rounded published beta
multiplied by rounded means. Already-rounded excess, other statistics and their
strict-state/measurability limits remain; no historical market contamination or
whole-comparator precision/availability claim is established.

## Reversal

Remove the both-original Float64 predicate/helper/dispatch and restore original
source coefficients for those pairs. This reopens FINDING-232, preserving all
separate accepted family corrections and thresholds.
