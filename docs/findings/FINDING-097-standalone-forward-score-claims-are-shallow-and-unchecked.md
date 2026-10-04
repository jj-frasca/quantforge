# FINDING-097: Standalone forward scores are shallow and unchecked

- **Date:** 2026-10-04
- **Severity:** Medium — independent forward evidence can drift or contradict its curve
- **Status:** Resolved by ADR-166

## Evidence

`ForwardScore` and `CrossSectionalForwardScore` accept negative bar counts, nonfinite statistics,
mutable curves, and points containing naive timestamps or nonpositive/nonfinite equities. A caller
can append to a score curve or reorder cross-sectional component evidence after validation.
`model_validate` of an unchecked score/point copy does not revalidate its fields. The outer
ADR-148/149 position boundaries reject many malformed scores and freeze their evidence, but pure
score results and independent points do not receive those protections.

TDD regressions construct each root directly, mutate caller/public curve and evidence lists, and
revalidate unchecked copies. They also test nonempty curve length/order/terminal identity and
curve points after the advertised score cutoff. These claims are invalid independently of any
position's symbol, universe, or freeze date.

## Impact and limits

The defect affects standalone derived evidence between computation and attachment or publication.
Existing complete position/store boundaries already protect their durable score graph; there is
no evidence of a corrupted generated book. Legacy absent evidence and empty curves are intentional,
not failures. Historical single-name trade counts may be absent, so no new beats-flag formula is
inferred from those records.

## Correction

ADR-166 validates intrinsic point/score geometry at the root, revalidates model instances, and
freezes curve/component collections without changing their JSON shapes. Position-specific identity
checks remain at positions. No data file, financial formula, threshold, or lifecycle rule changes.
