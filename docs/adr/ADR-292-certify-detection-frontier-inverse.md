# ADR-292: Solve the conditional normal-model frontier within its unique inverse domain

- **Status:** Accepted
- **Date:** 2026-10-15
- **Deciders:** Codex autonomous session 15, ISO 2026-W42
- **Resolves:** FINDING-244 (frontier fixed-iteration/tail/branch error)
- **Extends:** ADR-043
- **Relates to:** ADR-018, FINDING-164

## Context

The report-only frontier promises to solve s=b+z*sqrt((1+s*s/504)/T).
Eight iterations can return an unconverged finite value, and a fixed[-10,10]
erf/CDF inverse loses extreme tails. Some accepted requests have no finite
solution or multiple signed solutions. A finite iteration result is not a
validated frontier. Default long-history output agrees with the stated model;
no actual production graduate or historical calibration impact is established.

## Options considered

1. Stable inverse-normal quantile and algebra on the unique inverse domain.
   Explicit scientific contract, bounded work; some former requests now refuse.
2. More fixed iterations. Does not establish existence, uniqueness, convergence
   or tail correctness; reject.
3. Restrict all requests to power>=.5. Unnecessarily removes valid signed
   lower-power unique solutions; reject.
4. Choose among nonunique branches or extrapolate an infinite frontier.
   Requires a new interpretive policy; reject for this repair.

## Decision

Preserve ADR018's existing bar and the shared standard-error function exactly.
Replace only the frontier inverse/quantile calculation. Support the open unique
inverse regime abs(z)<sqrt(504*T), with finite positive T and 0<p<1.
Preserve existing count/bar coercion policy; general original-scalar hardening is
outside this slice. Retain valid signed lower-power solutions, p=.5 giving the original bar, and
N<2's existing zero-bar convention. Refuse unsupported boundary/nonunique/
unattainable requests honestly, without claiming every refused lower-tail
case has no algebraic roots. Finite request/bar/result evidence is required.

Use the standard-library inverse normal CDF and solve the existing equation
algebraically at its represented quantile and the original native bar. Exact
Fraction coefficients certify a=1-z*z/(504*T)>0 without rounded boundary
classification. For c=b*b-z*z/T and D=b*b-a*c, use (b+sqrt(D))/a for positive z
and c/(b+sqrt(D)) for negative z, avoiding cancellation in the latter. Preserve
z=0 as the exact original bar. Evaluate only the final square root/division
with a private Decimal160 ROUND_HALF_EVEN context, isolated from caller traps,
precision, rounding and flags. Independent Decimal300 monotone bisection and
scientific inverse-normal crosschecks must cover tails/near-critical/cancellation
cases; no universal exact transcendental-quantile claim is made. Do not change any bar, statistical model,
threshold, sharedSE calculation, search, reference scorer or accounting identity.

Qualify the DetectionFrontier description and active cold-memory interpretation.
Preserve its fields and factory shape; unsupported requests raise ValueError
rather than producing a finite claim.

This is a conditional iid-normal asymptotic approximation to crossing one bar,
not a universal guarantee for the composite search/graduation pipeline. It neither
certifies actual market power nor separates all other causes of calibration gaps.
Historical measurements and accepted ADR043 remain attributable and untouched.

## Verification and consequences

Public tests fail before production implementation. Retain all original frontier
assertions and add independent high-precision roots, supported-domain independent-equation
properties, extreme normal tails, unsupported regimes and caller
Decimal-state ownership. Independently audit exact sharedSE/bar/search/gate
source preservation; keep implementation/source snapshots outside permanent tests. No frozen source regeneration or calibration
reruns are needed: only report-derived frontiers change, with explicit code
provenance and no estimator/selector/gate change. Require independent final review,
foreground make check-all, explicit-path individual commit/push and exact CI.

## Reversal

Restore the old inverse solver/quantile and prior report documentation together,
retaining the written finding. This would reopen incorrect finite frontier claims;
no financial threshold or generated artifact is changed by either direction.
