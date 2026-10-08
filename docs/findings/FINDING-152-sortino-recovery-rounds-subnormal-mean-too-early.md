# FINDING-152: Sortino recovery rounds a subnormal mean too early

- **Date:** 2026-10-07
- **Severity:** Medium — a representable descriptive score is erased
- **Status:** Open

## Evidence

Independent ADR-209 review reproduced `sortino_ratio([-1, nextafter(0, 1), 1])`
as zero at revision f1891104. An 800-digit exact-float Decimal oracle for the
full-sample downside semi-deviation gives a representable rounded `4.4e-323`.
Original sum certification correctly rejects native zero, and stable normalized
summation recovers the residual, but dividing that sum by three rounds to zero
before annualization can recover it. This is distinct from original native mean
failure in F148/F149; the recovery itself loses the evidence.

Sortino is descriptive, so no gate/graduate effect is asserted. A separate ADR
and RED tests must govern rearrangement, including tiny downside scales where
reordering intermediate divisions can overflow despite a representable final
score. No correction, universal precision guarantee, threshold change or
generated-data rewrite is claimed here.
